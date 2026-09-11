import math
from typing import Any
import pandas as pd

EARTH_RADIUS_M = 6_371_000.0


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _finite_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna()


def calculate_statistics(samples: pd.DataFrame,
                         waypoints: pd.DataFrame,
                         events: pd.DataFrame) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "sample_count": int(len(samples)),
        "waypoint_count": int(len(waypoints)),
        "event_count": int(len(events)),
    }

    if samples.empty:
        return stats

    elapsed = _finite_series(samples["elapsed_ms"])
    if not elapsed.empty:
        stats["duration_s"] = float((elapsed.max() - elapsed.min()) / 1000.0)

    gps_mask = (
        samples["gps_valid"].fillna(False)
        & samples["gps_updated"].fillna(False)
        & samples["latitude_deg"].notna()
        & samples["longitude_deg"].notna()
    )
    gps = samples.loc[gps_mask].copy()
    stats["valid_gps_update_count"] = int(len(gps))

    if len(gps) >= 1:
        stats["start_latitude_deg"] = float(gps.iloc[0]["latitude_deg"])
        stats["start_longitude_deg"] = float(gps.iloc[0]["longitude_deg"])
        stats["end_latitude_deg"] = float(gps.iloc[-1]["latitude_deg"])
        stats["end_longitude_deg"] = float(gps.iloc[-1]["longitude_deg"])

        total_distance = 0.0
        for i in range(1, len(gps)):
            a = gps.iloc[i - 1]
            b = gps.iloc[i]
            total_distance += _haversine_m(
                float(a["latitude_deg"]),
                float(a["longitude_deg"]),
                float(b["latitude_deg"]),
                float(b["longitude_deg"]),
            )
        stats["total_distance_m"] = total_distance

    speed = _finite_series(samples.loc[samples["gps_valid"].fillna(False), "speed_mps"])
    if not speed.empty:
        stats["average_speed_mps"] = float(speed.mean())
        stats["max_speed_mps"] = float(speed.max())

    altitude = _finite_series(samples.loc[samples["gps_valid"].fillna(False), "gps_altitude_m"])
    if not altitude.empty:
        stats["min_gps_altitude_m"] = float(altitude.min())
        stats["max_gps_altitude_m"] = float(altitude.max())
        stats["gps_altitude_range_m"] = float(altitude.max() - altitude.min())

    temp = _finite_series(samples.loc[samples["bme_valid"].fillna(False), "temperature_c"])
    if not temp.empty:
        stats["average_temperature_c"] = float(temp.mean())
        stats["min_temperature_c"] = float(temp.min())
        stats["max_temperature_c"] = float(temp.max())

    humidity = _finite_series(samples.loc[samples["bme_valid"].fillna(False), "humidity_pct"])
    if not humidity.empty:
        stats["average_humidity_pct"] = float(humidity.mean())

    pressure = _finite_series(samples.loc[samples["bme_valid"].fillna(False), "pressure_hpa"])
    if not pressure.empty:
        stats["average_pressure_hpa"] = float(pressure.mean())

    return stats
