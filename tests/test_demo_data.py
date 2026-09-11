from pathlib import Path

from geotracker_studio.demo_data import generate_demo_session
from geotracker_studio import load_session


def test_generated_demo_session(tmp_path: Path):
    path = generate_demo_session(tmp_path)
    session = load_session(path)
    assert session.validation.ok
    assert len(session.samples) == 300
    assert len(session.waypoints) == 3
    assert len(session.events) == 7
    assert session.statistics['total_distance_m'] > 100
    assert session.statistics['valid_gps_update_count'] == 293
