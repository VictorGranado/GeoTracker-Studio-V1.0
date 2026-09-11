from pathlib import Path
import xml.etree.ElementTree as ET

from geotracker_studio import load_session
from geotracker_studio.demo_data import generate_demo_session
from geotracker_studio.exporters import (
    ExportOptions,
    export_gpx,
    export_kml,
    export_summary,
)

KML = {"k": "http://www.opengis.net/kml/2.2", "gx": "http://www.google.com/kml/ext/2.2"}
GPX = {"g": "http://www.topografix.com/GPX/1/1"}


def _session(tmp_path):
    return load_session(generate_demo_session(tmp_path / "demo"))


def test_export_summary_preserves_gps_gap(tmp_path):
    session = _session(tmp_path)
    s = export_summary(session)
    assert s.route_points == 293
    assert s.route_segments == 2
    assert s.waypoints == 3
    assert s.events == 6
    assert s.start_end_markers == 2


def test_kml_export_contains_timestamped_tracks_and_markers(tmp_path):
    session = _session(tmp_path)
    out = tmp_path / "route.kml"
    summary = export_kml(session, out)
    assert out.exists()
    assert summary.route_points == 293
    tree = ET.parse(out)
    root = tree.getroot()
    tracks = root.findall(".//gx:Track", KML)
    assert len(tracks) == 2
    coords = root.findall(".//gx:coord", KML)
    assert len(coords) == 293
    names = [n.text for n in root.findall(".//k:Placemark/k:name", KML)]
    assert "GeoTracker Route" in names
    assert "Start" in names
    assert "End" in names
    assert "Trail Entry" in names


def test_kml_without_timestamps_uses_line_strings(tmp_path):
    session = _session(tmp_path)
    out = tmp_path / "route_no_time.kml"
    export_kml(session, out, ExportOptions(include_timestamps=False))
    root = ET.parse(out).getroot()
    assert len(root.findall(".//k:LineString", KML)) == 2
    assert len(root.findall(".//gx:Track", KML)) == 0


def test_gpx_export_contains_two_track_segments(tmp_path):
    session = _session(tmp_path)
    out = tmp_path / "route.gpx"
    summary = export_gpx(session, out)
    assert out.exists()
    assert summary.route_segments == 2
    root = ET.parse(out).getroot()
    segments = root.findall(".//g:trkseg", GPX)
    assert len(segments) == 2
    points = root.findall(".//g:trkpt", GPX)
    assert len(points) == 293
    assert all(p.find("g:ele", GPX) is not None for p in points)
    assert all(p.find("g:time", GPX) is not None for p in points)


def test_export_options_can_remove_optional_content(tmp_path):
    session = _session(tmp_path)
    options = ExportOptions(
        include_altitude=False,
        include_timestamps=False,
        include_waypoints=False,
        include_events=False,
        include_start_end=False,
    )
    out = tmp_path / "minimal.gpx"
    summary = export_gpx(session, out, options)
    assert summary.waypoints == 0
    assert summary.events == 0
    assert summary.start_end_markers == 0
    root = ET.parse(out).getroot()
    assert root.findall(".//g:wpt", GPX) == []
    points = root.findall(".//g:trkpt", GPX)
    assert points
    assert all(p.find("g:ele", GPX) is None for p in points)
    assert all(p.find("g:time", GPX) is None for p in points)
