import argparse
import json
from .parser import load_session, GeoTrackerParseError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and summarize a GeoTracker v1.0 session."
    )
    parser.add_argument("session", help="Path to a GeoTracker session directory")
    args = parser.parse_args()

    try:
        session = load_session(args.session)
    except GeoTrackerParseError as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"GeoTracker session: {session.session_id}")
    print(f"Schema version:     {session.schema_version}")
    print()

    print("Validation")
    print("----------")
    print(session.validation)
    print()

    print("Statistics")
    print("----------")
    print(json.dumps(session.statistics, indent=2, default=str))

    return 0 if session.validation.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
