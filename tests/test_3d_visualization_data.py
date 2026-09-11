from pathlib import Path

import numpy as np

from geotracker_studio import load_session
from geotracker_studio.demo_data import generate_demo_session
from geotracker_studio.visualization_data import contiguous_valid_runs, route_3d_data


def _session(tmp_path):
    return load_session(generate_demo_session(tmp_path))


def test_route_3d_uses_relative_altitude(tmp_path):
    session = _session(tmp_path)
    route = route_3d_data(session.samples)
    assert route.valid.sum() == 293
    assert np.isclose(np.nanmin(route.relative_altitude_m[route.valid]), 0.0)
    assert np.nanmax(route.relative_altitude_m[route.valid]) > 7.0


def test_route_3d_preserves_metric_xy_scale(tmp_path):
    session = _session(tmp_path)
    route = route_3d_data(session.samples)
    assert np.ptp(route.x_m[route.valid]) > 10.0
    assert np.ptp(route.y_m[route.valid]) > 150.0


def test_contiguous_runs_preserve_demo_gps_gap(tmp_path):
    session = _session(tmp_path)
    route = route_3d_data(session.samples)
    runs = contiguous_valid_runs(route.valid)
    assert len(runs) == 2
    assert runs[0][-1] == 111
    assert runs[1][0] == 119


def test_route_3d_ids_align_with_samples(tmp_path):
    session = _session(tmp_path)
    route = route_3d_data(session.samples)
    assert len(route.sample_ids) == len(session.samples)
    assert route.sample_ids[0] == 0
    assert route.sample_ids[-1] == 299
