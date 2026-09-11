from __future__ import annotations

"""Pure basemap/tile planning utilities for GeoTracker Studio.

This module intentionally has no Qt dependency so tile planning can be tested
headlessly. GUI tile decoding/compositing lives in ``gui_basemap.py``.
"""

from dataclasses import dataclass
from pathlib import Path
import math
import os

TILE_SIZE = 256
WEB_MERCATOR_LAT_LIMIT = 85.05112878


@dataclass(frozen=True)
class TileProvider:
    key: str
    label: str
    url_template: str
    attribution: str
    max_zoom: int = 19
    min_zoom: int = 0


OPENSTREETMAP = TileProvider(
    key="osm",
    label="OpenStreetMap",
    url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution="© OpenStreetMap contributors",
    max_zoom=19,
)

PROVIDERS = {OPENSTREETMAP.key: OPENSTREETMAP}
PROVIDER_LABELS = {p.label: p for p in PROVIDERS.values()}


@dataclass(frozen=True)
class TilePlan:
    provider_key: str
    zoom: int
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    pixel_left: int
    pixel_top: int
    pixel_right: int
    pixel_bottom: int

    @property
    def tile_columns(self) -> int:
        return self.x_max - self.x_min + 1

    @property
    def tile_rows(self) -> int:
        return self.y_max - self.y_min + 1

    @property
    def tile_count(self) -> int:
        return self.tile_columns * self.tile_rows

    @property
    def width_px(self) -> int:
        return self.tile_columns * TILE_SIZE

    @property
    def height_px(self) -> int:
        return self.tile_rows * TILE_SIZE


def clamp_latitude(latitude_deg: float) -> float:
    return max(-WEB_MERCATOR_LAT_LIMIT, min(WEB_MERCATOR_LAT_LIMIT, float(latitude_deg)))


def latlon_to_global_pixel(latitude_deg: float, longitude_deg: float, zoom: int) -> tuple[float, float]:
    """Convert WGS84 lat/lon to Web-Mercator global pixel coordinates."""
    lat = math.radians(clamp_latitude(latitude_deg))
    lon = float(longitude_deg)
    world_px = TILE_SIZE * (2 ** int(zoom))
    x = (lon + 180.0) / 360.0 * world_px
    y = (1.0 - math.asinh(math.tan(lat)) / math.pi) / 2.0 * world_px
    return x, y


def global_pixel_to_latlon(x_px: float, y_px: float, zoom: int) -> tuple[float, float]:
    """Convert Web-Mercator global pixel coordinates to WGS84 lat/lon."""
    world_px = TILE_SIZE * (2 ** int(zoom))
    lon = float(x_px) / world_px * 360.0 - 180.0
    n = math.pi - 2.0 * math.pi * float(y_px) / world_px
    lat = math.degrees(math.atan(math.sinh(n)))
    return lat, lon


def _plan_at_zoom(
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
    zoom: int,
    padding_px: int,
) -> TilePlan:
    # NW / SE corners in global Web-Mercator pixel space.
    left, top = latlon_to_global_pixel(lat_max, lon_min, zoom)
    right, bottom = latlon_to_global_pixel(lat_min, lon_max, zoom)

    if right < left:
        # GeoTracker sessions are expected to be local; antimeridian-spanning
        # sessions are deliberately not supported in v1.0 basemap planning.
        raise ValueError("Basemap bounds cross the antimeridian, which is not supported in v1.0.")

    left -= padding_px
    right += padding_px
    top -= padding_px
    bottom += padding_px

    n = 2 ** zoom
    x_min = max(0, min(n - 1, int(math.floor(left / TILE_SIZE))))
    x_max = max(0, min(n - 1, int(math.floor((right - 1e-9) / TILE_SIZE))))
    y_min = max(0, min(n - 1, int(math.floor(top / TILE_SIZE))))
    y_max = max(0, min(n - 1, int(math.floor((bottom - 1e-9) / TILE_SIZE))))

    return TilePlan(
        provider_key="",
        zoom=zoom,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        pixel_left=x_min * TILE_SIZE,
        pixel_top=y_min * TILE_SIZE,
        pixel_right=(x_max + 1) * TILE_SIZE,
        pixel_bottom=(y_max + 1) * TILE_SIZE,
    )


def choose_tile_plan(
    lat_min: float,
    lon_min: float,
    lat_max: float,
    lon_max: float,
    provider: TileProvider = OPENSTREETMAP,
    preferred_zoom: int = 17,
    max_tiles: int = 16,
    padding_px: int = 96,
) -> TilePlan:
    """Choose one zoom level that covers the current route without bulk fetching.

    Only the single zoom level needed for the current session view is planned.
    ``max_tiles`` intentionally keeps downloads modest.
    """
    lat_min, lat_max = sorted((float(lat_min), float(lat_max)))
    lon_min, lon_max = sorted((float(lon_min), float(lon_max)))

    if not all(math.isfinite(v) for v in (lat_min, lon_min, lat_max, lon_max)):
        raise ValueError("Basemap bounds must be finite.")

    z_start = min(int(preferred_zoom), provider.max_zoom)
    for zoom in range(z_start, provider.min_zoom - 1, -1):
        plan = _plan_at_zoom(lat_min, lon_min, lat_max, lon_max, zoom, int(padding_px))
        if plan.tile_count <= max_tiles:
            return TilePlan(provider.key, **{k: getattr(plan, k) for k in (
                "zoom", "x_min", "x_max", "y_min", "y_max",
                "pixel_left", "pixel_top", "pixel_right", "pixel_bottom"
            )})

    raise ValueError("Could not create a bounded tile plan for this route.")


def tile_plan_latlon_bounds(plan: TilePlan) -> tuple[float, float, float, float]:
    """Return (lat_min, lon_min, lat_max, lon_max) for the full tile mosaic."""
    lat_max, lon_min = global_pixel_to_latlon(plan.pixel_left, plan.pixel_top, plan.zoom)
    lat_min, lon_max = global_pixel_to_latlon(plan.pixel_right, plan.pixel_bottom, plan.zoom)
    return lat_min, lon_min, lat_max, lon_max


def tile_url(provider: TileProvider, zoom: int, x: int, y: int) -> str:
    return provider.url_template.format(z=int(zoom), x=int(x), y=int(y))


def default_tile_cache_root() -> Path:
    """Return a user-local cache path without requiring app installation."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "GeoTrackerStudio" / "tile_cache"
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "geotracker_studio" / "tile_cache"
    return Path.home() / ".cache" / "geotracker_studio" / "tile_cache"


def tile_cache_path(provider: TileProvider, zoom: int, x: int, y: int, cache_root: Path | None = None) -> Path:
    root = Path(cache_root) if cache_root is not None else default_tile_cache_root()
    return root / provider.key / str(int(zoom)) / str(int(x)) / f"{int(y)}.png"
