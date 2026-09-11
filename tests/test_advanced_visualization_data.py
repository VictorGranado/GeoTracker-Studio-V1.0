from pathlib import Path

import numpy as np

from geotracker_studio import load_session
from geotracker_studio.demo_data import generate_demo_session
from geotracker_studio.visualization_data import (
    OVERLAYS_BY_LABEL,
    local_projection_reference,
    overlay_values,
    project_latlon_to_local_m,
    robust_value_range,
)


def _session(tmp_path):
    return load_session(generate_demo_session(tmp_path))


def test_local_projection_is_meter_scaled(tmp_path):
    session = _session(tmp_path)
    lat0, lon0 = local_projection_reference(session.samples)
    x, y = project_latlon_to_local_m([lat0, lat0 + 0.001], [lon0, lon0], lat0, lon0)
    assert abs(x[0]) < 1e-9
    assert 110 < y[1] < 112


def test_local_projection_preserves_demo_route_scale(tmp_path):
    session = _session(tmp_path)
    lat0, lon0 = local_projection_reference(session.samples)
    lat = session.samples['latitude_deg'].to_numpy(dtype=float)
    lon = session.samples['longitude_deg'].to_numpy(dtype=float)
    x, y = project_latlon_to_local_m(lat, lon, lat0, lon0)
    assert np.nanmax(y) - np.nanmin(y) > 150
    assert np.nanmax(x) - np.nanmin(x) > 10


def test_overlay_values_respect_gps_outage(tmp_path):
    session = _session(tmp_path)
    values = overlay_values(session.samples, OVERLAYS_BY_LABEL['GPS quality (HDOP)'])
    assert np.isnan(values[112:119]).all()
    assert np.isfinite(values[111])
    assert np.isfinite(values[119])


def test_overlay_robust_range(tmp_path):
    session = _session(tmp_path)
    values = overlay_values(session.samples, OVERLAYS_BY_LABEL['Temperature'])
    limits = robust_value_range(values)
    assert limits is not None
    lo, hi = limits
    assert lo < hi
    assert lo < 24.5
    assert hi > 23.0
