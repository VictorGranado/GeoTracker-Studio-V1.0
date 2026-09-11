from __future__ import annotations

"""Qt raster-basemap loading and compositing for GeoTracker Studio."""

from dataclasses import dataclass
from pathlib import Path
import os
import tempfile
import urllib.request
import urllib.error

import numpy as np
import pandas as pd
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter

from .basemap_data import (
    OPENSTREETMAP,
    PROVIDERS,
    TilePlan,
    choose_tile_plan,
    tile_cache_path,
    tile_plan_latlon_bounds,
    tile_url,
)
from .visualization_data import project_latlon_to_local_m


USER_AGENT = "GeoTrackerStudio/1.0 (desktop field-data visualization app)"


class BasemapLoadError(RuntimeError):
    pass


@dataclass
class BasemapRaster:
    provider_key: str
    provider_label: str
    attribution: str
    zoom: int
    tile_count: int
    rgba: np.ndarray  # row-major, north-at-top RGBA uint8
    x_min_m: float
    x_max_m: float
    y_min_m: float
    y_max_m: float
    failures: int = 0

    @property
    def width_m(self) -> float:
        return self.x_max_m - self.x_min_m

    @property
    def height_m(self) -> float:
        return self.y_max_m - self.y_min_m


def _valid_route_bounds(samples: pd.DataFrame) -> tuple[float, float, float, float]:
    lat = pd.to_numeric(samples["latitude_deg"], errors="coerce")
    lon = pd.to_numeric(samples["longitude_deg"], errors="coerce")
    if "gps_valid" in samples:
        valid = samples["gps_valid"].fillna(False).astype(bool)
    else:
        valid = pd.Series(True, index=samples.index)
    mask = valid & lat.notna() & lon.notna()
    if not mask.any():
        raise BasemapLoadError("This session has no valid GPS coordinates for a basemap.")
    return float(lat[mask].min()), float(lon[mask].min()), float(lat[mask].max()), float(lon[mask].max())


def _download_tile(provider, z: int, x: int, y: int, cache_root: Path | None = None) -> bytes:
    path = tile_cache_path(provider, z, x, y, cache_root)
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes()

    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        tile_url(provider, z, x, y),
        headers={"User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BasemapLoadError(f"Could not download map tile {z}/{x}/{y}: {exc}") from exc

    if not data:
        raise BasemapLoadError(f"Map tile {z}/{x}/{y} returned no data.")

    # Atomic cache write so an interrupted request never leaves a broken tile.
    fd, tmp_name = tempfile.mkstemp(prefix="gt_tile_", suffix=".png", dir=str(path.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_bytes(data)
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return data


def _decode_tile(data: bytes) -> QImage:
    image = QImage.fromData(data)
    if image.isNull():
        raise BasemapLoadError("Downloaded tile could not be decoded as an image.")
    return image.convertToFormat(QImage.Format_RGBA8888)


def _placeholder_tile() -> QImage:
    image = QImage(256, 256, QImage.Format_RGBA8888)
    image.fill(QColor("#202832"))
    return image


def _qimage_to_rgba(image: QImage) -> np.ndarray:
    image = image.convertToFormat(QImage.Format_RGBA8888)
    ptr = image.bits()
    arr = np.frombuffer(ptr, dtype=np.uint8, count=image.sizeInBytes())
    arr = arr.reshape((image.height(), image.bytesPerLine() // 4, 4))[:, : image.width(), :]
    return arr.copy()


def load_session_basemap(
    samples: pd.DataFrame,
    lat0: float,
    lon0: float,
    provider_key: str = "osm",
    preferred_zoom: int = 17,
    max_tiles: int = 16,
    cache_root: Path | None = None,
) -> BasemapRaster:
    if provider_key not in PROVIDERS:
        raise BasemapLoadError(f"Unknown basemap provider: {provider_key}")
    provider = PROVIDERS[provider_key]

    lat_min, lon_min, lat_max, lon_max = _valid_route_bounds(samples)
    plan = choose_tile_plan(
        lat_min, lon_min, lat_max, lon_max,
        provider=provider,
        preferred_zoom=preferred_zoom,
        max_tiles=max_tiles,
        padding_px=96,
    )

    mosaic = QImage(plan.width_px, plan.height_px, QImage.Format_RGBA8888)
    mosaic.fill(QColor("#202832"))
    painter = QPainter(mosaic)
    failures = 0
    successes = 0
    try:
        for tx in range(plan.x_min, plan.x_max + 1):
            for ty in range(plan.y_min, plan.y_max + 1):
                try:
                    tile = _decode_tile(_download_tile(provider, plan.zoom, tx, ty, cache_root))
                    successes += 1
                except BasemapLoadError:
                    tile = _placeholder_tile()
                    failures += 1
                dx = (tx - plan.x_min) * 256
                dy = (ty - plan.y_min) * 256
                painter.drawImage(QRect(dx, dy, 256, 256), tile)
    finally:
        painter.end()

    if successes == 0:
        raise BasemapLoadError(
            "No map tiles could be loaded. Check your internet connection, or switch the basemap off."
        )

    full_lat_min, full_lon_min, full_lat_max, full_lon_max = tile_plan_latlon_bounds(plan)
    # Convert SW and NE corners into the same local metric coordinate system used by the route.
    x, y = project_latlon_to_local_m(
        [full_lat_min, full_lat_max],
        [full_lon_min, full_lon_max],
        lat0,
        lon0,
    )
    x_min_m, x_max_m = sorted((float(x[0]), float(x[1])))
    y_min_m, y_max_m = sorted((float(y[0]), float(y[1])))

    return BasemapRaster(
        provider_key=provider.key,
        provider_label=provider.label,
        attribution=provider.attribution,
        zoom=plan.zoom,
        tile_count=plan.tile_count,
        rgba=_qimage_to_rgba(mosaic),
        x_min_m=x_min_m,
        x_max_m=x_max_m,
        y_min_m=y_min_m,
        y_max_m=y_max_m,
        failures=failures,
    )
