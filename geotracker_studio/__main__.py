"""Allow GeoTracker Studio to be launched with ``python -m geotracker_studio``."""

from .app import main


if __name__ == "__main__":
    raise SystemExit(main())
