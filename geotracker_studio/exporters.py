from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import xml.etree.ElementTree as ET

import pandas as pd

KML_NS = "http://www.opengis.net/kml/2.2"
GX_NS = "http://www.google.com/kml/ext/2.2"
GPX_NS = "http://www.topografix.com/GPX/1/1"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
GT_NS = "https://geotracker.local/schema/1.0"

ET.register_namespace("", KML_NS)
ET.register_namespace("gx", GX_NS)
ET.register_namespace("xsi", XSI_NS)
ET.register_namespace("gt", GT_NS)


def _q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


@dataclass(frozen=True)
class ExportOptions:
    include_altitude: bool = True
    include_timestamps: bool = True
    include_waypoints: bool = True
    include_events: bool = True
    include_start_end: bool = True


@dataclass(frozen=True)
class ExportSummary:
    route_points: int
    route_segments: int
    waypoints: int
    events: int
    start_end_markers: int


def _is_finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _iso_time(value) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    ts = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _route_rows(session) -> pd.DataFrame:
    s = session.samples.copy()
    required = {"sample_id", "gps_valid", "latitude_deg", "longitude_deg"}
    if not required.issubset(s.columns):
        return s.iloc[0:0].copy()

    valid = (
        s["gps_valid"].fillna(False).astype(bool)
        & pd.to_numeric(s["latitude_deg"], errors="coerce").notna()
        & pd.to_numeric(s["longitude_deg"], errors="coerce").notna()
    )
    if "gps_updated" in s.columns:
        valid &= s["gps_updated"].fillna(False).astype(bool)
    return s.loc[valid].copy()


def _route_runs(session) -> list[pd.DataFrame]:
    route = _route_rows(session)
    if route.empty:
        return []

    original_indices = route.index.to_numpy()
    breaks = [0]
    for i in range(1, len(route)):
        if int(original_indices[i]) != int(original_indices[i - 1]) + 1:
            breaks.append(i)
    breaks.append(len(route))
    return [route.iloc[breaks[i]:breaks[i + 1]].copy() for i in range(len(breaks) - 1)]


def export_summary(session, options: ExportOptions = ExportOptions()) -> ExportSummary:
    runs = _route_runs(session)
    route_points = sum(len(run) for run in runs)
    wp = len(session.waypoints) if options.include_waypoints else 0
    if options.include_events:
        events = session.events
        if not events.empty and {"latitude_deg", "longitude_deg"}.issubset(events.columns):
            mask = (
                pd.to_numeric(events["latitude_deg"], errors="coerce").notna()
                & pd.to_numeric(events["longitude_deg"], errors="coerce").notna()
            )
            ev = int(mask.sum())
        else:
            ev = 0
    else:
        ev = 0
    se = min(route_points, 2) if options.include_start_end else 0
    return ExportSummary(route_points, len(runs), wp, ev, se)


def _description_text(session) -> str:
    md = session.metadata
    stats = session.statistics
    parts = [
        f"GeoTracker session {session.session_id}",
        f"Device: {md.get('device_name', 'GeoTracker')}",
        f"Firmware: {md.get('firmware_version', 'unknown')}",
        f"Schema: {md.get('schema_version', 'unknown')}",
    ]
    if stats.get("duration_s") is not None:
        parts.append(f"Duration: {float(stats['duration_s']):.1f} s")
    if stats.get("total_distance_m") is not None:
        parts.append(f"Distance: {float(stats['total_distance_m']):.1f} m")
    return "\n".join(parts)


def _add_kml_extended_data(parent, session) -> None:
    ext = ET.SubElement(parent, _q(KML_NS, "ExtendedData"))
    values = {
        "session_id": session.session_id,
        "device_name": session.metadata.get("device_name", ""),
        "firmware_version": session.metadata.get("firmware_version", ""),
        "schema_version": session.metadata.get("schema_version", ""),
        "sample_count": len(session.samples),
        "waypoint_count": len(session.waypoints),
        "event_count": len(session.events),
    }
    for key, value in values.items():
        data = ET.SubElement(ext, _q(KML_NS, "Data"), {"name": str(key)})
        ET.SubElement(data, _q(KML_NS, "value")).text = str(value)


def _kml_point(folder, name: str, lat, lon, alt, timestamp, description: str,
               options: ExportOptions) -> bool:
    if not (_is_finite(lat) and _is_finite(lon)):
        return False
    placemark = ET.SubElement(folder, _q(KML_NS, "Placemark"))
    ET.SubElement(placemark, _q(KML_NS, "name")).text = str(name)
    if description:
        ET.SubElement(placemark, _q(KML_NS, "description")).text = description
    if options.include_timestamps:
        when = _iso_time(timestamp)
        if when:
            ts = ET.SubElement(placemark, _q(KML_NS, "TimeStamp"))
            ET.SubElement(ts, _q(KML_NS, "when")).text = when
    point = ET.SubElement(placemark, _q(KML_NS, "Point"))
    if options.include_altitude and _is_finite(alt):
        ET.SubElement(point, _q(KML_NS, "altitudeMode")).text = "absolute"
        coord = f"{float(lon):.8f},{float(lat):.8f},{float(alt):.3f}"
    else:
        coord = f"{float(lon):.8f},{float(lat):.8f}"
    ET.SubElement(point, _q(KML_NS, "coordinates")).text = coord
    return True


def export_kml(session, path: str | Path, options: ExportOptions = ExportOptions()) -> ExportSummary:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    runs = _route_runs(session)

    root = ET.Element(_q(KML_NS, "kml"))
    doc = ET.SubElement(root, _q(KML_NS, "Document"))
    ET.SubElement(doc, _q(KML_NS, "name")).text = f"GeoTracker — {session.session_id}"
    ET.SubElement(doc, _q(KML_NS, "description")).text = _description_text(session)
    _add_kml_extended_data(doc, session)

    route_pm = ET.SubElement(doc, _q(KML_NS, "Placemark"))
    ET.SubElement(route_pm, _q(KML_NS, "name")).text = "GeoTracker Route"
    ET.SubElement(route_pm, _q(KML_NS, "description")).text = _description_text(session)

    if options.include_timestamps:
        multi = ET.SubElement(route_pm, _q(GX_NS, "MultiTrack"))
        ET.SubElement(multi, _q(GX_NS, "interpolate")).text = "0"
        for run in runs:
            track = ET.SubElement(multi, _q(GX_NS, "Track"))
            ET.SubElement(track, _q(KML_NS, "altitudeMode")).text = (
                "absolute" if options.include_altitude else "clampToGround"
            )
            for _, row in run.iterrows():
                when = _iso_time(row.get("timestamp_utc"))
                if when:
                    ET.SubElement(track, _q(KML_NS, "when")).text = when
                lon = float(row["longitude_deg"])
                lat = float(row["latitude_deg"])
                alt = float(row["gps_altitude_m"]) if options.include_altitude and _is_finite(row.get("gps_altitude_m")) else 0.0
                ET.SubElement(track, _q(GX_NS, "coord")).text = f"{lon:.8f} {lat:.8f} {alt:.3f}"
    else:
        geom = ET.SubElement(route_pm, _q(KML_NS, "MultiGeometry"))
        for run in runs:
            line = ET.SubElement(geom, _q(KML_NS, "LineString"))
            ET.SubElement(line, _q(KML_NS, "tessellate")).text = "1"
            ET.SubElement(line, _q(KML_NS, "altitudeMode")).text = (
                "absolute" if options.include_altitude else "clampToGround"
            )
            coords = []
            for _, row in run.iterrows():
                lon = float(row["longitude_deg"])
                lat = float(row["latitude_deg"])
                if options.include_altitude and _is_finite(row.get("gps_altitude_m")):
                    coords.append(f"{lon:.8f},{lat:.8f},{float(row['gps_altitude_m']):.3f}")
                else:
                    coords.append(f"{lon:.8f},{lat:.8f}")
            ET.SubElement(line, _q(KML_NS, "coordinates")).text = " ".join(coords)

    route = _route_rows(session)
    markers = ET.SubElement(doc, _q(KML_NS, "Folder"))
    ET.SubElement(markers, _q(KML_NS, "name")).text = "Markers"
    start_end_count = 0
    if options.include_start_end and not route.empty:
        for name, row in (("Start", route.iloc[0]), ("End", route.iloc[-1])):
            if _kml_point(markers, name, row.get("latitude_deg"), row.get("longitude_deg"),
                          row.get("gps_altitude_m"), row.get("timestamp_utc"),
                          f"{name} of GeoTracker session {session.session_id}", options):
                start_end_count += 1

    wp_count = 0
    if options.include_waypoints and not session.waypoints.empty:
        wp_folder = ET.SubElement(doc, _q(KML_NS, "Folder"))
        ET.SubElement(wp_folder, _q(KML_NS, "name")).text = "Waypoints"
        for _, row in session.waypoints.iterrows():
            name = row.get("label") or row.get("waypoint_id") or "Waypoint"
            desc_parts = [str(row.get("waypoint_id", ""))]
            if str(row.get("note", "")).strip():
                desc_parts.append(str(row.get("note")))
            if _kml_point(wp_folder, name, row.get("latitude_deg"), row.get("longitude_deg"),
                          row.get("gps_altitude_m"), row.get("timestamp_utc"),
                          "\n".join(p for p in desc_parts if p), options):
                wp_count += 1

    event_count = 0
    if options.include_events and not session.events.empty:
        ev_folder = ET.SubElement(doc, _q(KML_NS, "Folder"))
        ET.SubElement(ev_folder, _q(KML_NS, "name")).text = "Events"
        for _, row in session.events.iterrows():
            event_type = row.get("event_type") or "Event"
            desc = str(row.get("note", "") or row.get("value", "") or row.get("event_id", ""))
            if _kml_point(ev_folder, event_type, row.get("latitude_deg"), row.get("longitude_deg"),
                          row.get("gps_altitude_m"), row.get("timestamp_utc"), desc, options):
                event_count += 1

    tree = ET.ElementTree(root)
    ET.register_namespace("", KML_NS)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    tree.write(path, encoding="utf-8", xml_declaration=True)

    return ExportSummary(sum(len(r) for r in runs), len(runs), wp_count, event_count, start_end_count)


def _gpx_point(parent, tag: str, lat, lon, alt, timestamp, name: str | None,
               desc: str | None, options: ExportOptions):
    if not (_is_finite(lat) and _is_finite(lon)):
        return None
    node = ET.SubElement(parent, _q(GPX_NS, tag), {
        "lat": f"{float(lat):.8f}",
        "lon": f"{float(lon):.8f}",
    })
    if options.include_altitude and _is_finite(alt):
        ET.SubElement(node, _q(GPX_NS, "ele")).text = f"{float(alt):.3f}"
    if options.include_timestamps:
        when = _iso_time(timestamp)
        if when:
            ET.SubElement(node, _q(GPX_NS, "time")).text = when
    if name:
        ET.SubElement(node, _q(GPX_NS, "name")).text = str(name)
    if desc:
        ET.SubElement(node, _q(GPX_NS, "desc")).text = str(desc)
    return node


def export_gpx(session, path: str | Path, options: ExportOptions = ExportOptions()) -> ExportSummary:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    runs = _route_runs(session)

    root = ET.Element(_q(GPX_NS, "gpx"), {
        "version": "1.1",
        "creator": "GeoTracker Studio v1.0",
        _q(XSI_NS, "schemaLocation"): f"{GPX_NS} http://www.topografix.com/GPX/1/1/gpx.xsd",
    })

    metadata = ET.SubElement(root, _q(GPX_NS, "metadata"))
    ET.SubElement(metadata, _q(GPX_NS, "name")).text = f"GeoTracker {session.session_id}"
    ET.SubElement(metadata, _q(GPX_NS, "desc")).text = _description_text(session)
    if options.include_timestamps:
        start = _iso_time(session.metadata.get("start_time_utc"))
        if start:
            ET.SubElement(metadata, _q(GPX_NS, "time")).text = start
    ext = ET.SubElement(metadata, _q(GPX_NS, "extensions"))
    for tag, value in {
        "session_id": session.session_id,
        "device_name": session.metadata.get("device_name", ""),
        "firmware_version": session.metadata.get("firmware_version", ""),
        "schema_version": session.metadata.get("schema_version", ""),
    }.items():
        ET.SubElement(ext, _q(GT_NS, tag)).text = str(value)

    route = _route_rows(session)
    start_end_count = 0
    if options.include_start_end and not route.empty:
        for name, row in (("Start", route.iloc[0]), ("End", route.iloc[-1])):
            if _gpx_point(root, "wpt", row.get("latitude_deg"), row.get("longitude_deg"),
                          row.get("gps_altitude_m"), row.get("timestamp_utc"), name,
                          f"{name} of GeoTracker session {session.session_id}", options) is not None:
                start_end_count += 1

    wp_count = 0
    if options.include_waypoints:
        for _, row in session.waypoints.iterrows():
            name = row.get("label") or row.get("waypoint_id") or "Waypoint"
            desc = str(row.get("note", "") or row.get("waypoint_id", ""))
            if _gpx_point(root, "wpt", row.get("latitude_deg"), row.get("longitude_deg"),
                          row.get("gps_altitude_m"), row.get("timestamp_utc"), name, desc, options) is not None:
                wp_count += 1

    event_count = 0
    if options.include_events:
        for _, row in session.events.iterrows():
            name = row.get("event_type") or "Event"
            desc = str(row.get("note", "") or row.get("value", "") or row.get("event_id", ""))
            if _gpx_point(root, "wpt", row.get("latitude_deg"), row.get("longitude_deg"),
                          row.get("gps_altitude_m"), row.get("timestamp_utc"), name, desc, options) is not None:
                event_count += 1

    track = ET.SubElement(root, _q(GPX_NS, "trk"))
    ET.SubElement(track, _q(GPX_NS, "name")).text = f"GeoTracker Route — {session.session_id}"
    ET.SubElement(track, _q(GPX_NS, "desc")).text = _description_text(session)
    for run in runs:
        seg = ET.SubElement(track, _q(GPX_NS, "trkseg"))
        for _, row in run.iterrows():
            _gpx_point(seg, "trkpt", row.get("latitude_deg"), row.get("longitude_deg"),
                       row.get("gps_altitude_m"), row.get("timestamp_utc"), None, None, options)

    tree = ET.ElementTree(root)
    ET.register_namespace("", GPX_NS)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    tree.write(path, encoding="utf-8", xml_declaration=True)

    return ExportSummary(sum(len(r) for r in runs), len(runs), wp_count, event_count, start_end_count)
