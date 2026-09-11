from pathlib import Path

from geotracker_studio import load_session


EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "example_data"
    / "2026-09-08_231530"
)


def test_example_session_loads():
    session = load_session(EXAMPLE)
    assert session.validation.ok
    assert session.schema_version == "1.0"
    assert len(session.samples) == 8
    assert len(session.waypoints) == 2
    assert len(session.events) == 4


def test_boolean_fields_are_parsed():
    session = load_session(EXAMPLE)
    assert bool(session.samples.iloc[0]["gps_valid"]) is True
    assert bool(session.samples.iloc[0]["gps_updated"]) is True


def test_statistics_are_calculated():
    session = load_session(EXAMPLE)
    stats = session.statistics
    assert stats["sample_count"] == 8
    assert stats["waypoint_count"] == 2
    assert stats["event_count"] == 4
    assert stats["duration_s"] == 7.0
    assert stats["total_distance_m"] > 0
    assert stats["max_speed_mps"] >= stats["average_speed_mps"]


def test_filtered_views():
    session = load_session(EXAMPLE)
    assert len(session.gps_updates) == 7
    assert len(session.environment_samples) == 8
    assert len(session.magnetometer_samples) == 8
    assert len(session.imu_samples) == 8
