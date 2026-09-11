from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
import math

from .schema import SAMPLES_COLUMNS, WAYPOINT_COLUMNS, EVENT_COLUMNS


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def generate_demo_session(base_dir: str | Path) -> Path:
    """Generate a realistic fabricated GeoTracker session for GUI development."""
    base = Path(base_dir)
    session_dir = base / '2026-09-09_161500_DEMO'
    session_dir.mkdir(parents=True, exist_ok=True)

    start = datetime(2026, 9, 9, 22, 15, 0, tzinfo=timezone.utc)
    count = 300

    metadata = [
        ('schema_version', '1.0'),
        ('session_id', session_dir.name),
        ('device_name', 'GeoTracker v1.0'),
        ('firmware_version', '1.0-demo'),
        ('start_time_utc', _iso(start)),
        ('log_interval_ms', '1000'),
        ('coordinate_system', 'WGS84'),
        ('units', 'SI'),
    ]

    with (session_dir / 'session_info.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['key', 'value'])
        writer.writerows(metadata)

    sample_rows = []
    lat0 = 43.82310
    lon0 = -111.79240

    for i in range(count):
        t = start + timedelta(seconds=i)
        angle = i / 52.0
        north_m = i * 0.72 + 9.0 * math.sin(angle)
        east_m = 18.0 * math.sin(i / 67.0) + i * 0.20
        lat = lat0 + north_m / 111_111.0
        lon = lon0 + east_m / (111_111.0 * math.cos(math.radians(lat0)))

        gps_valid = not (112 <= i <= 118)
        gps_updated = gps_valid
        fix_type = 3 if gps_valid else 0
        sats = 10 + int(2 * math.sin(i / 31.0)) if gps_valid else 0
        altitude = 1481.0 + 0.020 * i + 2.5 * math.sin(i / 43.0)
        speed = max(0.25, 1.35 + 0.35 * math.sin(i / 28.0) + 0.08 * math.sin(i / 5.0))
        course = (12.0 + 22.0 * math.sin(i / 48.0)) % 360

        temperature = 22.6 + 0.006 * i + 0.35 * math.sin(i / 38.0)
        humidity = 41.5 - 0.010 * i + 0.8 * math.sin(i / 54.0)
        pressure = 848.7 - 0.006 * i + 0.18 * math.sin(i / 37.0)
        pressure_alt = 1461.0 + 0.45 * i / 10.0 + 1.4 * math.sin(i / 45.0)

        heading = (course + 2.0 * math.sin(i / 9.0)) % 360
        mx = -13.0 + 3.0 * math.sin(i / 19.0)
        my = 9.0 + 2.5 * math.cos(i / 17.0)
        mz = 26.0 + 1.2 * math.sin(i / 23.0)
        strength = math.sqrt(mx * mx + my * my + mz * mz)

        ax = 0.22 * math.sin(i / 4.0)
        ay = 9.45 + 0.10 * math.cos(i / 6.0)
        az = -1.20 + 0.12 * math.sin(i / 7.0)
        gx = 0.30 * math.sin(i / 8.0)
        gy = 0.22 * math.cos(i / 10.0)
        gz = 0.18 * math.sin(i / 5.5)
        pitch = -2.0 + 1.1 * math.sin(i / 24.0)
        roll = 2.8 + 1.4 * math.cos(i / 29.0)

        row = {
            'sample_id': i,
            'timestamp_utc': _iso(t),
            'elapsed_ms': i * 1000,
            'gps_valid': int(gps_valid),
            'gps_updated': int(gps_updated),
            'gps_fix_type': fix_type,
            'satellites': sats,
            'latitude_deg': f'{lat:.6f}' if gps_valid else '',
            'longitude_deg': f'{lon:.6f}' if gps_valid else '',
            'gps_altitude_m': f'{altitude:.2f}' if gps_valid else '',
            'speed_mps': f'{speed:.3f}' if gps_valid else '',
            'course_deg': f'{course:.2f}' if gps_valid else '',
            'hdop': f'{0.82 + 0.18 * abs(math.sin(i / 40.0)):.2f}' if gps_valid else '',
            'pdop': f'{1.30 + 0.25 * abs(math.sin(i / 42.0)):.2f}' if gps_valid else '',
            'vdop': f'{1.02 + 0.20 * abs(math.cos(i / 44.0)):.2f}' if gps_valid else '',
            'bme_valid': 1,
            'temperature_c': f'{temperature:.2f}',
            'humidity_pct': f'{humidity:.2f}',
            'pressure_hpa': f'{pressure:.2f}',
            'pressure_altitude_m': f'{pressure_alt:.2f}',
            'mag_valid': 1,
            'mag_x_ut': f'{mx:.2f}',
            'mag_y_ut': f'{my:.2f}',
            'mag_z_ut': f'{mz:.2f}',
            'mag_strength_ut': f'{strength:.2f}',
            'heading_deg': f'{heading:.2f}',
            'imu_valid': 1,
            'accel_x_mps2': f'{ax:.3f}',
            'accel_y_mps2': f'{ay:.3f}',
            'accel_z_mps2': f'{az:.3f}',
            'gyro_x_dps': f'{gx:.3f}',
            'gyro_y_dps': f'{gy:.3f}',
            'gyro_z_dps': f'{gz:.3f}',
            'pitch_deg': f'{pitch:.2f}',
            'roll_deg': f'{roll:.2f}',
        }
        sample_rows.append(row)

    with (session_dir / 'samples.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SAMPLES_COLUMNS)
        writer.writeheader()
        writer.writerows(sample_rows)

    waypoint_indices = [62, 164, 254]
    waypoint_rows = []
    event_rows = []

    for n, idx in enumerate(waypoint_indices, start=1):
        source = sample_rows[idx]
        waypoint_id = f'WP{n:03d}'
        waypoint_rows.append({
            'waypoint_id': waypoint_id,
            'source_sample_id': idx,
            'timestamp_utc': source['timestamp_utc'],
            'elapsed_ms': source['elapsed_ms'],
            'latitude_deg': source['latitude_deg'],
            'longitude_deg': source['longitude_deg'],
            'gps_altitude_m': source['gps_altitude_m'],
            'heading_deg': source['heading_deg'],
            'label': ['Trail Entry', 'Survey Point', 'Return Marker'][n - 1],
            'note': ['Start of field segment', 'Fabricated environmental sample location', 'Reference point before return'][n - 1],
        })
        event_rows.append({
            'event_id': f'EV{n + 1:03d}',
            'source_sample_id': idx,
            'timestamp_utc': source['timestamp_utc'],
            'elapsed_ms': source['elapsed_ms'],
            'event_type': 'WAYPOINT_CREATED',
            'latitude_deg': source['latitude_deg'],
            'longitude_deg': source['longitude_deg'],
            'gps_altitude_m': source['gps_altitude_m'],
            'value': waypoint_id,
            'note': '',
        })

    event_rows.insert(0, {
        'event_id': 'EV001',
        'source_sample_id': 0,
        'timestamp_utc': sample_rows[0]['timestamp_utc'],
        'elapsed_ms': 0,
        'event_type': 'SESSION_START',
        'latitude_deg': sample_rows[0]['latitude_deg'],
        'longitude_deg': sample_rows[0]['longitude_deg'],
        'gps_altitude_m': sample_rows[0]['gps_altitude_m'],
        'value': '',
        'note': 'Fabricated development session',
    })
    event_rows.extend([
        {
            'event_id': 'EV005', 'source_sample_id': 112,
            'timestamp_utc': sample_rows[112]['timestamp_utc'], 'elapsed_ms': 112000,
            'event_type': 'GPS_FIX_LOST', 'latitude_deg': '', 'longitude_deg': '',
            'gps_altitude_m': '', 'value': '', 'note': 'Simulated GPS obstruction'
        },
        {
            'event_id': 'EV006', 'source_sample_id': 119,
            'timestamp_utc': sample_rows[119]['timestamp_utc'], 'elapsed_ms': 119000,
            'event_type': 'GPS_FIX_ACQUIRED', 'latitude_deg': sample_rows[119]['latitude_deg'],
            'longitude_deg': sample_rows[119]['longitude_deg'],
            'gps_altitude_m': sample_rows[119]['gps_altitude_m'], 'value': '3', 'note': '3D fix restored'
        },
        {
            'event_id': 'EV007', 'source_sample_id': count - 1,
            'timestamp_utc': sample_rows[-1]['timestamp_utc'], 'elapsed_ms': (count - 1) * 1000,
            'event_type': 'SESSION_END', 'latitude_deg': sample_rows[-1]['latitude_deg'],
            'longitude_deg': sample_rows[-1]['longitude_deg'],
            'gps_altitude_m': sample_rows[-1]['gps_altitude_m'], 'value': '', 'note': ''
        },
    ])

    with (session_dir / 'waypoints.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=WAYPOINT_COLUMNS)
        writer.writeheader()
        writer.writerows(waypoint_rows)

    with (session_dir / 'events.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=EVENT_COLUMNS)
        writer.writeheader()
        writer.writerows(event_rows)

    return session_dir
