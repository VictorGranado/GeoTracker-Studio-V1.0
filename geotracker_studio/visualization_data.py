from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class MetricDefinition:
    label: str
    column: str
    unit: str
    validity_column: str | None = None


@dataclass(frozen=True)
class OverlayDefinition:
    label: str
    column: str | None
    unit: str
    validity_column: str | None = None
    reverse_scale: bool = False


METRICS: tuple[MetricDefinition, ...] = (
    MetricDefinition('GPS altitude', 'gps_altitude_m', 'm', 'gps_valid'),
    MetricDefinition('Speed', 'speed_mps', 'm/s', 'gps_valid'),
    MetricDefinition('Satellites', 'satellites', 'count', 'gps_valid'),
    MetricDefinition('Temperature', 'temperature_c', '°C', 'bme_valid'),
    MetricDefinition('Humidity', 'humidity_pct', '% RH', 'bme_valid'),
    MetricDefinition('Pressure', 'pressure_hpa', 'hPa', 'bme_valid'),
    MetricDefinition('Pressure altitude', 'pressure_altitude_m', 'm', 'bme_valid'),
    MetricDefinition('Heading', 'heading_deg', '°', 'mag_valid'),
    MetricDefinition('Magnetic field strength', 'mag_strength_ut', 'µT', 'mag_valid'),
    MetricDefinition('Pitch', 'pitch_deg', '°', 'imu_valid'),
    MetricDefinition('Roll', 'roll_deg', '°', 'imu_valid'),
    MetricDefinition('Accel X', 'accel_x_mps2', 'm/s²', 'imu_valid'),
    MetricDefinition('Accel Y', 'accel_y_mps2', 'm/s²', 'imu_valid'),
    MetricDefinition('Accel Z', 'accel_z_mps2', 'm/s²', 'imu_valid'),
    MetricDefinition('Gyro X', 'gyro_x_dps', '°/s', 'imu_valid'),
    MetricDefinition('Gyro Y', 'gyro_y_dps', '°/s', 'imu_valid'),
    MetricDefinition('Gyro Z', 'gyro_z_dps', '°/s', 'imu_valid'),
)

METRICS_BY_LABEL = {m.label: m for m in METRICS}

OVERLAYS: tuple[OverlayDefinition, ...] = (
    OverlayDefinition('Normal route', None, ''),
    OverlayDefinition('Temperature', 'temperature_c', '°C', 'bme_valid'),
    OverlayDefinition('GPS altitude', 'gps_altitude_m', 'm', 'gps_valid'),
    OverlayDefinition('Speed', 'speed_mps', 'm/s', 'gps_valid'),
    OverlayDefinition('Humidity', 'humidity_pct', '% RH', 'bme_valid'),
    OverlayDefinition('Pressure', 'pressure_hpa', 'hPa', 'bme_valid'),
    OverlayDefinition('Heading', 'heading_deg', '°', 'mag_valid'),
    OverlayDefinition('Magnetic field', 'mag_strength_ut', 'µT', 'mag_valid'),
    OverlayDefinition('GPS quality (HDOP)', 'hdop', 'HDOP', 'gps_valid', reverse_scale=True),
)

OVERLAYS_BY_LABEL = {o.label: o for o in OVERLAYS}


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def local_projection_reference(samples: pd.DataFrame) -> tuple[float, float]:
    lat = pd.to_numeric(samples.get('latitude_deg'), errors='coerce').to_numpy(dtype=float)
    lon = pd.to_numeric(samples.get('longitude_deg'), errors='coerce').to_numpy(dtype=float)
    valid = np.isfinite(lat) & np.isfinite(lon)
    if not valid.any():
        return 0.0, 0.0
    return float(np.nanmean(lat[valid])), float(np.nanmean(lon[valid]))


def project_latlon_to_local_m(lat, lon, lat0: float, lon0: float) -> tuple[np.ndarray, np.ndarray]:
    """Equirectangular local projection for small field-scale GeoTracker sessions."""
    lat_arr = np.asarray(lat, dtype=float)
    lon_arr = np.asarray(lon, dtype=float)
    x = EARTH_RADIUS_M * np.radians(lon_arr - lon0) * math.cos(math.radians(lat0))
    y = EARTH_RADIUS_M * np.radians(lat_arr - lat0)
    return x, y


def cumulative_distance_m(samples: pd.DataFrame) -> np.ndarray:
    """Return cumulative GPS route distance for every sample row."""
    n = len(samples)
    out = np.zeros(n, dtype=float)
    if n == 0:
        return out

    lat = pd.to_numeric(samples.get('latitude_deg'), errors='coerce').to_numpy(dtype=float)
    lon = pd.to_numeric(samples.get('longitude_deg'), errors='coerce').to_numpy(dtype=float)

    if 'gps_valid' in samples:
        valid_flag = samples['gps_valid'].fillna(False).astype(bool).to_numpy()
    else:
        valid_flag = np.ones(n, dtype=bool)

    valid = valid_flag & np.isfinite(lat) & np.isfinite(lon)
    total = 0.0
    prev = None
    for i in range(n):
        if valid[i]:
            current = (float(lat[i]), float(lon[i]))
            if prev is not None:
                total += haversine_m(prev[0], prev[1], current[0], current[1])
            prev = current
        out[i] = total
    return out


def x_axis_values(samples: pd.DataFrame, mode: str) -> tuple[np.ndarray, str]:
    if mode == 'Distance (m)':
        return cumulative_distance_m(samples), 'Distance (m)'
    if mode == 'Sample ID':
        return pd.to_numeric(samples['sample_id'], errors='coerce').to_numpy(dtype=float), 'Sample ID'

    elapsed = pd.to_numeric(samples['elapsed_ms'], errors='coerce').to_numpy(dtype=float) / 1000.0
    return elapsed, 'Elapsed time (s)'


def metric_values(samples: pd.DataFrame, definition: MetricDefinition) -> np.ndarray:
    values = pd.to_numeric(samples[definition.column], errors='coerce').to_numpy(dtype=float)
    if definition.validity_column and definition.validity_column in samples:
        valid = samples[definition.validity_column].fillna(False).astype(bool).to_numpy()
        values = np.where(valid, values, np.nan)
    return values


def overlay_values(samples: pd.DataFrame, definition: OverlayDefinition) -> np.ndarray:
    if definition.column is None:
        return np.full(len(samples), np.nan, dtype=float)
    values = pd.to_numeric(samples[definition.column], errors='coerce').to_numpy(dtype=float)
    if definition.validity_column and definition.validity_column in samples:
        valid = samples[definition.validity_column].fillna(False).astype(bool).to_numpy()
        values = np.where(valid, values, np.nan)
    return values


def robust_value_range(values: np.ndarray) -> tuple[float, float] | None:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if not len(finite):
        return None
    if len(finite) < 10:
        lo, hi = float(np.min(finite)), float(np.max(finite))
    else:
        lo, hi = np.percentile(finite, [2.0, 98.0])
        lo, hi = float(lo), float(hi)
    if math.isclose(lo, hi):
        pad = max(abs(lo) * 0.01, 1e-6)
        lo, hi = lo - pad, hi + pad
    return lo, hi

@dataclass(frozen=True)
class Route3DData:
    x_m: np.ndarray
    y_m: np.ndarray
    altitude_m: np.ndarray
    relative_altitude_m: np.ndarray
    valid: np.ndarray
    sample_ids: np.ndarray
    lat0: float
    lon0: float
    base_altitude_m: float


def route_3d_data(samples: pd.DataFrame) -> Route3DData:
    """Build meter-scaled X/Y coordinates plus GPS altitude for 3D rendering."""
    n = len(samples)
    lat = pd.to_numeric(samples.get('latitude_deg'), errors='coerce').to_numpy(dtype=float)
    lon = pd.to_numeric(samples.get('longitude_deg'), errors='coerce').to_numpy(dtype=float)
    altitude = pd.to_numeric(samples.get('gps_altitude_m'), errors='coerce').to_numpy(dtype=float)
    ids = pd.to_numeric(samples.get('sample_id'), errors='coerce').fillna(-1).astype(int).to_numpy()

    if 'gps_valid' in samples:
        gps_valid = samples['gps_valid'].fillna(False).astype(bool).to_numpy()
    else:
        gps_valid = np.ones(n, dtype=bool)

    lat0, lon0 = local_projection_reference(samples)
    x, y = project_latlon_to_local_m(lat, lon, lat0, lon0)
    valid = gps_valid & np.isfinite(x) & np.isfinite(y) & np.isfinite(altitude)

    if valid.any():
        base_alt = float(np.nanmin(altitude[valid]))
    else:
        base_alt = 0.0

    relative = altitude - base_alt
    return Route3DData(
        x_m=x,
        y_m=y,
        altitude_m=altitude,
        relative_altitude_m=relative,
        valid=valid,
        sample_ids=ids,
        lat0=lat0,
        lon0=lon0,
        base_altitude_m=base_alt,
    )


def contiguous_valid_runs(valid: np.ndarray) -> list[np.ndarray]:
    """Return index arrays for contiguous True runs, preserving GPS gaps."""
    mask = np.asarray(valid, dtype=bool)
    if not len(mask):
        return []
    indices = np.where(mask)[0]
    if not len(indices):
        return []
    split_at = np.where(np.diff(indices) > 1)[0] + 1
    return [run for run in np.split(indices, split_at) if len(run)]

