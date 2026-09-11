from pathlib import Path
import pandas as pd

from .models import Session
from .schema import (
    SCHEMA_VERSION,
    REQUIRED_SESSION_KEYS,
    SAMPLES_COLUMNS,
    WAYPOINT_COLUMNS,
    EVENT_COLUMNS,
    BOOLEAN_COLUMNS,
    SAMPLE_NUMERIC_COLUMNS,
    WAYPOINT_NUMERIC_COLUMNS,
    EVENT_NUMERIC_COLUMNS,
    SUPPORTED_FIX_TYPES,
)
from .statistics import calculate_statistics
from .validation import ValidationReport


class GeoTrackerParseError(Exception):
    pass


def _load_metadata(path: Path, report: ValidationReport) -> dict[str, str]:
    if not path.exists():
        report.add_error("Missing required file: session_info.csv")
        return {}

    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:
        report.add_error(f"Could not read session_info.csv: {exc}")
        return {}

    if list(df.columns) != ["key", "value"]:
        report.add_error("session_info.csv must contain exactly the columns: key,value")
        return {}

    metadata = {
        str(row["key"]).strip(): str(row["value"]).strip()
        for _, row in df.iterrows()
        if str(row["key"]).strip()
    }

    missing = REQUIRED_SESSION_KEYS - set(metadata)
    for key in sorted(missing):
        report.add_error(f"Missing session metadata key: {key}")

    schema_version = metadata.get("schema_version")
    if schema_version and schema_version != SCHEMA_VERSION:
        report.add_error(
            f"Unsupported schema version {schema_version!r}; "
            f"this parser supports {SCHEMA_VERSION!r}."
        )
    elif schema_version:
        report.add_info(f"Schema version {schema_version} supported.")

    if metadata.get("coordinate_system") not in {"", "WGS84"}:
        report.add_warning(
            f"Unexpected coordinate system: {metadata.get('coordinate_system')!r}"
        )

    if metadata.get("units") not in {"", "SI"}:
        report.add_warning(f"Unexpected units declaration: {metadata.get('units')!r}")

    return metadata


def _read_csv(path: Path, required_columns: list[str],
              report: ValidationReport, optional: bool) -> pd.DataFrame:
    if not path.exists():
        if optional:
            report.add_warning(f"{path.name} not found; using an empty table.")
            return pd.DataFrame(columns=required_columns)
        report.add_error(f"Missing required file: {path.name}")
        return pd.DataFrame(columns=required_columns)

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        report.add_error(f"Could not read {path.name}: {exc}")
        return pd.DataFrame(columns=required_columns)

    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        report.add_error(
            f"{path.name} is missing required columns: {', '.join(missing)}"
        )

    extra = [c for c in df.columns if c not in required_columns]
    if extra:
        report.add_warning(
            f"{path.name} contains unknown columns that will be preserved: "
            + ", ".join(extra)
        )

    return df


def _coerce_numeric(df: pd.DataFrame, columns: list[str],
                    report: ValidationReport, filename: str) -> None:
    for col in columns:
        if col not in df:
            continue
        original_nonempty = df[col].notna() & (df[col].astype(str).str.strip() != "")
        converted = pd.to_numeric(df[col], errors="coerce")
        invalid_count = int((original_nonempty & converted.isna()).sum())
        if invalid_count:
            report.add_warning(
                f"{filename}: {invalid_count} invalid numeric value(s) in {col}."
            )
        df[col] = converted


def _coerce_booleans(df: pd.DataFrame, report: ValidationReport) -> None:
    for col in BOOLEAN_COLUMNS:
        if col not in df:
            continue

        numeric = pd.to_numeric(df[col], errors="coerce")
        invalid = numeric.notna() & ~numeric.isin([0, 1])
        if invalid.any():
            report.add_warning(
                f"samples.csv: {int(invalid.sum())} non-0/1 value(s) in {col}."
            )
        df[col] = numeric.map({0: False, 1: True}).astype("boolean")


def _coerce_timestamp(df: pd.DataFrame, filename: str,
                      report: ValidationReport) -> None:
    if "timestamp_utc" not in df:
        return

    original = df["timestamp_utc"].copy()
    converted = pd.to_datetime(original, errors="coerce", utc=True)
    nonempty = original.notna() & (original.astype(str).str.strip() != "")
    invalid = nonempty & converted.isna()
    if invalid.any():
        report.add_warning(
            f"{filename}: {int(invalid.sum())} invalid timestamp(s)."
        )
    df["timestamp_utc"] = converted


def _validate_sample_ranges(df: pd.DataFrame, report: ValidationReport) -> None:
    if df.empty:
        report.add_warning("samples.csv contains no rows.")
        return

    if "sample_id" in df and df["sample_id"].duplicated().any():
        report.add_error("samples.csv contains duplicate sample_id values.")

    if "elapsed_ms" in df:
        elapsed = df["elapsed_ms"].dropna()
        if (elapsed < 0).any():
            report.add_error("samples.csv contains negative elapsed_ms values.")
        if not elapsed.is_monotonic_increasing:
            report.add_warning("elapsed_ms is not monotonically increasing.")

    if "latitude_deg" in df:
        bad = df["latitude_deg"].notna() & ~df["latitude_deg"].between(-90, 90)
        if bad.any():
            report.add_warning(f"{int(bad.sum())} latitude value(s) are outside [-90, 90].")

    if "longitude_deg" in df:
        bad = df["longitude_deg"].notna() & ~df["longitude_deg"].between(-180, 180)
        if bad.any():
            report.add_warning(f"{int(bad.sum())} longitude value(s) are outside [-180, 180].")

    if "heading_deg" in df:
        bad = df["heading_deg"].notna() & ~df["heading_deg"].between(0, 360, inclusive="left")
        if bad.any():
            report.add_warning(f"{int(bad.sum())} heading value(s) are outside [0, 360).")

    if "gps_fix_type" in df:
        values = set(df["gps_fix_type"].dropna().astype(int).tolist())
        unsupported = sorted(values - SUPPORTED_FIX_TYPES)
        if unsupported:
            report.add_warning(f"Unsupported gps_fix_type value(s): {unsupported}")


def load_session(session_path: str | Path) -> Session:
    path = Path(session_path).expanduser().resolve()
    report = ValidationReport()

    if not path.exists():
        raise GeoTrackerParseError(f"Session directory does not exist: {path}")
    if not path.is_dir():
        raise GeoTrackerParseError(f"Session path is not a directory: {path}")

    metadata = _load_metadata(path / "session_info.csv", report)

    samples = _read_csv(
        path / "samples.csv", SAMPLES_COLUMNS, report, optional=False
    )
    waypoints = _read_csv(
        path / "waypoints.csv", WAYPOINT_COLUMNS, report, optional=True
    )
    events = _read_csv(
        path / "events.csv", EVENT_COLUMNS, report, optional=True
    )

    _coerce_numeric(samples, SAMPLE_NUMERIC_COLUMNS, report, "samples.csv")
    _coerce_numeric(waypoints, WAYPOINT_NUMERIC_COLUMNS, report, "waypoints.csv")
    _coerce_numeric(events, EVENT_NUMERIC_COLUMNS, report, "events.csv")

    _coerce_booleans(samples, report)

    _coerce_timestamp(samples, "samples.csv", report)
    _coerce_timestamp(waypoints, "waypoints.csv", report)
    _coerce_timestamp(events, "events.csv", report)

    _validate_sample_ranges(samples, report)

    if report.ok:
        report.add_info(f"samples.csv loaded: {len(samples)} sample(s).")
        report.add_info(f"waypoints.csv loaded: {len(waypoints)} waypoint(s).")
        report.add_info(f"events.csv loaded: {len(events)} event(s).")

    statistics = calculate_statistics(samples, waypoints, events)

    return Session(
        path=path,
        metadata=metadata,
        samples=samples,
        waypoints=waypoints,
        events=events,
        validation=report,
        statistics=statistics,
    )
