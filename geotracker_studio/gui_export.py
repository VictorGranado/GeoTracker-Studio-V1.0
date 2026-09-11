from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .exporters import ExportOptions, export_gpx, export_kml, export_summary


class ExportPage(QWidget):
    exportCompleted = Signal(str)

    def __init__(self):
        super().__init__()
        self.session = None

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 24)
        root.setSpacing(16)

        title = QLabel('Export')
        title.setObjectName('PageTitle')
        subtitle = QLabel('Create portable route files for Google Earth, GIS, and GPS software')
        subtitle.setObjectName('PageSubtitle')
        root.addWidget(title)
        root.addWidget(subtitle)

        formats = QHBoxLayout()
        formats.setSpacing(12)
        formats.addWidget(self._format_card(
            'KML',
            'Google Earth / GIS',
            'Exports the route as timestamped gx:Track data when timestamps are enabled, plus waypoints, events, and start/end markers.'
        ))
        formats.addWidget(self._format_card(
            'GPX',
            'GPS / navigation software',
            'Exports standards-based GPX 1.1 tracks with separate segments across GPS outages and optional elevation/time fields.'
        ))
        root.addLayout(formats)

        options_panel = QFrame()
        options_panel.setObjectName('Panel')
        options_layout = QVBoxLayout(options_panel)
        options_layout.setContentsMargins(18, 16, 18, 18)
        options_layout.setSpacing(12)

        options_title = QLabel('Export contents')
        options_title.setObjectName('PanelTitle')
        options_layout.addWidget(options_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(10)
        self.altitude = QCheckBox('Include altitude')
        self.timestamps = QCheckBox('Include timestamps')
        self.waypoints = QCheckBox('Include waypoints')
        self.events = QCheckBox('Include geolocated events')
        self.start_end = QCheckBox('Include start / end markers')
        for box in [self.altitude, self.timestamps, self.waypoints, self.events, self.start_end]:
            box.setChecked(True)
            box.stateChanged.connect(self._refresh_summary)
        grid.addWidget(self.altitude, 0, 0)
        grid.addWidget(self.timestamps, 0, 1)
        grid.addWidget(self.waypoints, 1, 0)
        grid.addWidget(self.events, 1, 1)
        grid.addWidget(self.start_end, 2, 0)
        options_layout.addLayout(grid)

        self.summary_label = QLabel('Load a session to preview export contents.')
        self.summary_label.setObjectName('Muted')
        self.summary_label.setWordWrap(True)
        options_layout.addWidget(self.summary_label)
        root.addWidget(options_panel)

        destination = QFrame()
        destination.setObjectName('Panel')
        dl = QVBoxLayout(destination)
        dl.setContentsMargins(18, 16, 18, 18)
        dl.setSpacing(12)
        dtitle = QLabel('Create export')
        dtitle.setObjectName('PanelTitle')
        dl.addWidget(dtitle)

        explainer = QLabel(
            'The original GeoTracker CSV session is never modified. Export files are generated from the current in-memory Session object.'
        )
        explainer.setObjectName('Muted')
        explainer.setWordWrap(True)
        dl.addWidget(explainer)

        buttons = QHBoxLayout()
        self.kml_btn = QPushButton('Export KML…')
        self.kml_btn.setObjectName('PrimaryButton')
        self.gpx_btn = QPushButton('Export GPX…')
        self.gpx_btn.setObjectName('PrimaryButton')
        self.both_btn = QPushButton('Export both to folder…')
        self.both_btn.setObjectName('SecondaryButton')
        self.kml_btn.clicked.connect(self._export_kml)
        self.gpx_btn.clicked.connect(self._export_gpx)
        self.both_btn.clicked.connect(self._export_both)
        buttons.addWidget(self.kml_btn)
        buttons.addWidget(self.gpx_btn)
        buttons.addWidget(self.both_btn)
        buttons.addStretch(1)
        dl.addLayout(buttons)

        self.last_export = QLabel('No exports created in this run.')
        self.last_export.setObjectName('Muted')
        self.last_export.setWordWrap(True)
        dl.addWidget(self.last_export)
        root.addWidget(destination)
        root.addStretch(1)

        self._set_buttons_enabled(False)

    @staticmethod
    def _format_card(format_name: str, subtitle: str, body: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName('Card')
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(5)
        name = QLabel(format_name)
        name.setObjectName('CardValue')
        sub = QLabel(subtitle)
        sub.setObjectName('CardLabel')
        text = QLabel(body)
        text.setObjectName('CardDetail')
        text.setWordWrap(True)
        layout.addWidget(name)
        layout.addWidget(sub)
        layout.addSpacing(5)
        layout.addWidget(text)
        layout.addStretch(1)
        return frame

    def _set_buttons_enabled(self, enabled: bool):
        self.kml_btn.setEnabled(enabled)
        self.gpx_btn.setEnabled(enabled)
        self.both_btn.setEnabled(enabled)

    def set_session(self, session):
        self.session = session
        self._set_buttons_enabled(session is not None)
        self.last_export.setText('No exports created for this session yet.')
        self._refresh_summary()

    def _options(self) -> ExportOptions:
        return ExportOptions(
            include_altitude=self.altitude.isChecked(),
            include_timestamps=self.timestamps.isChecked(),
            include_waypoints=self.waypoints.isChecked(),
            include_events=self.events.isChecked(),
            include_start_end=self.start_end.isChecked(),
        )

    def _refresh_summary(self):
        if self.session is None:
            self.summary_label.setText('Load a session to preview export contents.')
            return
        s = export_summary(self.session, self._options())
        self.summary_label.setText(
            f'{s.route_points} route point(s) · {s.route_segments} track segment(s) · '
            f'{s.waypoints} waypoint(s) · {s.events} geolocated event(s) · '
            f'{s.start_end_markers} start/end marker(s)'
        )

    def _default_name(self, suffix: str) -> str:
        session_id = self.session.session_id if self.session is not None else 'geotracker_session'
        return f'{session_id}.{suffix}'

    def _success(self, label: str, path: Path, summary):
        text = (
            f'{label} created successfully\n{path}\n\n'
            f'{summary.route_points} route points · {summary.route_segments} segment(s) · '
            f'{summary.waypoints} waypoint(s) · {summary.events} event(s)'
        )
        self.last_export.setText(text.replace('\n', ' · ', 1))
        self.exportCompleted.emit(f'Exported {label}: {path.name}')
        QMessageBox.information(self, 'Export complete', text)

    def _failure(self, label: str, exc: Exception):
        QMessageBox.critical(self, f'{label} export failed', str(exc))

    def _export_kml(self):
        if self.session is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export GeoTracker KML', self._default_name('kml'), 'KML files (*.kml)'
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != '.kml':
            path = path.with_suffix('.kml')
        try:
            summary = export_kml(self.session, path, self._options())
            self._success('KML', path, summary)
        except Exception as exc:
            self._failure('KML', exc)

    def _export_gpx(self):
        if self.session is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export GeoTracker GPX', self._default_name('gpx'), 'GPX files (*.gpx)'
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != '.gpx':
            path = path.with_suffix('.gpx')
        try:
            summary = export_gpx(self.session, path, self._options())
            self._success('GPX', path, summary)
        except Exception as exc:
            self._failure('GPX', exc)

    def _export_both(self):
        if self.session is None:
            return
        directory = QFileDialog.getExistingDirectory(self, 'Choose export folder')
        if not directory:
            return
        folder = Path(directory)
        kml_path = folder / self._default_name('kml')
        gpx_path = folder / self._default_name('gpx')
        try:
            kml_summary = export_kml(self.session, kml_path, self._options())
            gpx_summary = export_gpx(self.session, gpx_path, self._options())
            self.last_export.setText(f'Created {kml_path.name} and {gpx_path.name} in {folder}')
            self.exportCompleted.emit(f'Exported KML + GPX to {folder}')
            QMessageBox.information(
                self,
                'Export complete',
                f'Created both export formats in:\n{folder}\n\n'
                f'{kml_summary.route_points} route points · {kml_summary.route_segments} track segment(s)'
            )
        except Exception as exc:
            self._failure('KML / GPX', exc)
