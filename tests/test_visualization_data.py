from pathlib import Path

import numpy as np

from geotracker_studio import load_session
from geotracker_studio.demo_data import generate_demo_session
from geotracker_studio.visualization_data import (
    METRICS_BY_LABEL,
    cumulative_distance_m,
    metric_values,
    x_axis_values,
)


def _session(tmp_path):
    return load_session(generate_demo_session(tmp_path))


def test_cumulative_distance_is_monotonic(tmp_path):
    session = _session(tmp_path)
    d = cumulative_distance_m(session.samples)
    assert len(d) == len(session.samples)
    assert np.all(np.diff(d) >= -1e-9)
    assert d[-1] > 100


def test_graph_axes_match_samples(tmp_path):
    session = _session(tmp_path)
    for mode in ['Elapsed time (s)', 'Distance (m)', 'Sample ID']:
        x, label = x_axis_values(session.samples, mode)
        assert len(x) == len(session.samples)
        assert label


def test_metric_validity_masks_gps_outage(tmp_path):
    session = _session(tmp_path)
    values = metric_values(session.samples, METRICS_BY_LABEL['GPS altitude'])
    assert np.isnan(values[112:119]).all()
    assert np.isfinite(values[111])
    assert np.isfinite(values[119])
