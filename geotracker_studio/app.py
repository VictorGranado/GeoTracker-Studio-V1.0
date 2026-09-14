from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .demo_data import generate_demo_session
from .gui_main import MainWindow
from .resources import resource_path, user_data_root


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('GeoTracker Studio')
    app.setApplicationDisplayName('GeoTracker Studio v1.0.1')
    app.setApplicationVersion('1.0.1')
    app.setOrganizationName('GeoTracker')

    icon_path = resource_path('assets/geotracker_studio.png')
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # The fabricated development session lives in writable user data so the
    # packaged application never needs to modify its installation directory.
    demo_root = user_data_root() / 'demo_data'
    demo_session = generate_demo_session(demo_root)

    window = MainWindow(startup_session=demo_session)
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
