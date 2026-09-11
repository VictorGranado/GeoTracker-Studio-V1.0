"""Windows/PyInstaller entry point for GeoTracker Studio.

This launcher imports the application as a package instead of executing
geotracker_studio/app.py directly. That preserves package context so the
relative imports used inside the geotracker_studio package work correctly.
"""

from geotracker_studio.app import main


if __name__ == "__main__":
    raise SystemExit(main())
