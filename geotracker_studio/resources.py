from __future__ import annotations

from pathlib import Path
import os
import sys

def resource_path(relative: str | Path) -> Path:
    """Resolve bundled/static resources in source and PyInstaller builds."""
    relative = Path(relative)
    if hasattr(sys, '_MEIPASS'):
        return Path(getattr(sys, '_MEIPASS')) / relative
    return Path(__file__).resolve().parents[1] / relative

def user_data_root() -> Path:
    """Writable application-data directory for demo data and future settings."""
    if os.name == 'nt' and os.environ.get('LOCALAPPDATA'):
        root = Path(os.environ['LOCALAPPDATA']) / 'GeoTrackerStudio'
    elif os.environ.get('XDG_DATA_HOME'):
        root = Path(os.environ['XDG_DATA_HOME']) / 'geotracker_studio'
    else:
        root = Path.home() / '.local' / 'share' / 'geotracker_studio'
    root.mkdir(parents=True, exist_ok=True)
    return root
