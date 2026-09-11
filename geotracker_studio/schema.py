"""GeoTracker Data Contract v1.0 definitions."""

SCHEMA_VERSION = "1.0"

REQUIRED_SESSION_KEYS = {
    "schema_version",
    "session_id",
    "device_name",
    "firmware_version",
    "start_time_utc",
    "log_interval_ms",
    "coordinate_system",
    "units",
}

SAMPLES_COLUMNS = [
    "sample_id",
    "timestamp_utc",
    "elapsed_ms",
    "gps_valid",
    "gps_updated",
    "gps_fix_type",
    "satellites",
    "latitude_deg",
    "longitude_deg",
    "gps_altitude_m",
    "speed_mps",
    "course_deg",
    "hdop",
    "pdop",
    "vdop",
    "bme_valid",
    "temperature_c",
    "humidity_pct",
    "pressure_hpa",
    "pressure_altitude_m",
    "mag_valid",
    "mag_x_ut",
    "mag_y_ut",
    "mag_z_ut",
    "mag_strength_ut",
    "heading_deg",
    "imu_valid",
    "accel_x_mps2",
    "accel_y_mps2",
    "accel_z_mps2",
    "gyro_x_dps",
    "gyro_y_dps",
    "gyro_z_dps",
    "pitch_deg",
    "roll_deg",
]

WAYPOINT_COLUMNS = [
    "waypoint_id",
    "source_sample_id",
    "timestamp_utc",
    "elapsed_ms",
    "latitude_deg",
    "longitude_deg",
    "gps_altitude_m",
    "heading_deg",
    "label",
    "note",
]

EVENT_COLUMNS = [
    "event_id",
    "source_sample_id",
    "timestamp_utc",
    "elapsed_ms",
    "event_type",
    "latitude_deg",
    "longitude_deg",
    "gps_altitude_m",
    "value",
    "note",
]

BOOLEAN_COLUMNS = [
    "gps_valid",
    "gps_updated",
    "bme_valid",
    "mag_valid",
    "imu_valid",
]

SAMPLE_NUMERIC_COLUMNS = [
    c for c in SAMPLES_COLUMNS
    if c not in BOOLEAN_COLUMNS and c not in {"timestamp_utc"}
]

WAYPOINT_NUMERIC_COLUMNS = [
    "source_sample_id",
    "elapsed_ms",
    "latitude_deg",
    "longitude_deg",
    "gps_altitude_m",
    "heading_deg",
]

EVENT_NUMERIC_COLUMNS = [
    "source_sample_id",
    "elapsed_ms",
    "latitude_deg",
    "longitude_deg",
    "gps_altitude_m",
]

SUPPORTED_FIX_TYPES = {0, 2, 3}
