from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .gui_theme import APP_QSS
from .gui_visualization import DataGraphsPage, Route3DPage, RouteMapPage, SelectionController
from .gui_export import ExportPage
from .parser import GeoTrackerParseError, load_session
from .resources import resource_path


def _fmt(value, digits=1, suffix='') -> str:
    if value is None:
        return '—'
    try:
        if pd.isna(value):
            return '—'
    except Exception:
        pass
    if isinstance(value, float):
        return f'{value:.{digits}f}{suffix}'
    return f'{value}{suffix}'


class MetricCard(QFrame):
    def __init__(self, label: str, value: str = '—', detail: str = ''):
        super().__init__()
        self.setObjectName('Card')
        self.setMinimumHeight(112)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setObjectName('CardLabel')
        self.value_label = QLabel(value)
        self.value_label.setObjectName('CardValue')
        self.detail_label = QLabel(detail)
        self.detail_label.setObjectName('CardDetail')
        self.detail_label.setWordWrap(True)

        layout.addWidget(lbl)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)
        layout.addStretch(1)

    def set_value(self, value: str, detail: str = ''):
        self.value_label.setText(value)
        self.detail_label.setText(detail)


class Panel(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName('Panel')
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(16, 14, 16, 16)
        self.outer.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName('PanelTitle')
        self.outer.addWidget(title_label)


class OverviewPage(QWidget):
    openSessionRequested = Signal()

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 24)
        root.setSpacing(18)

        title = QLabel('Overview')
        title.setObjectName('PageTitle')
        subtitle = QLabel('Session summary and system health')
        subtitle.setObjectName('PageSubtitle')
        root.addWidget(title)
        root.addWidget(subtitle)

        self.demo_banner = QFrame()
        self.demo_banner.setObjectName('DemoBanner')
        banner_row = QHBoxLayout(self.demo_banner)
        banner_row.setContentsMargins(14, 10, 12, 10)
        banner_row.setSpacing(10)
        badge = QLabel('DEMO DATA')
        badge.setObjectName('DemoBadge')
        banner_row.addWidget(badge)
        banner_text = QLabel('Fabricated sample session loaded. Open a GeoTracker session folder to analyze real field data.')
        banner_text.setObjectName('DemoBannerText')
        banner_text.setWordWrap(True)
        banner_row.addWidget(banner_text, 1)
        banner_open = QPushButton('Open session…')
        banner_open.setObjectName('SecondaryButton')
        banner_open.clicked.connect(self.openSessionRequested.emit)
        banner_row.addWidget(banner_open)
        self.demo_banner.hide()
        root.addWidget(self.demo_banner)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        self.cards = {
            'duration': MetricCard('Duration'),
            'distance': MetricCard('Distance'),
            'avg_speed': MetricCard('Average speed'),
            'altitude': MetricCard('Altitude range'),
            'samples': MetricCard('Samples'),
            'gps': MetricCard('Valid GPS updates'),
            'temperature': MetricCard('Temperature'),
            'environment': MetricCard('Environment'),
        }
        for idx, card in enumerate(self.cards.values()):
            grid.addWidget(card, idx // 4, idx % 4)
        root.addLayout(grid)

        lower = QHBoxLayout()
        lower.setSpacing(12)

        self.session_panel = Panel('Session information')
        self.session_info = QLabel('No session loaded.')
        self.session_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.session_info.setWordWrap(True)
        self.session_panel.outer.addWidget(self.session_info)

        self.validation_panel = Panel('Validation')
        self.validation_status = QLabel('No session loaded.')
        self.validation_status.setWordWrap(True)
        self.validation_panel.outer.addWidget(self.validation_status)

        lower.addWidget(self.session_panel, 3)
        lower.addWidget(self.validation_panel, 2)
        root.addLayout(lower)

        preview = Panel('Recent samples')
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(7)
        self.preview_table.setHorizontalHeaderLabels([
            'Sample', 'Time', 'Latitude', 'Longitude', 'Altitude (m)', 'Temp (°C)', 'Heading (°)'
        ])
        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        preview.outer.addWidget(self.preview_table)
        root.addWidget(preview, 1)

    def set_demo_state(self, is_demo: bool):
        self.demo_banner.setVisible(bool(is_demo))

    def set_session(self, session):
        s = session.statistics
        duration = s.get('duration_s')
        duration_text = f'{int(duration // 60)}m {int(duration % 60)}s' if duration is not None else '—'
        self.cards['duration'].set_value(duration_text, 'Elapsed session time')
        self.cards['distance'].set_value(_fmt(s.get('total_distance_m'), 1, ' m'), 'Haversine route distance')
        self.cards['avg_speed'].set_value(_fmt(s.get('average_speed_mps'), 2, ' m/s'), 'Valid GPS samples')

        amin = s.get('min_gps_altitude_m')
        amax = s.get('max_gps_altitude_m')
        altitude = f'{amin:.1f}–{amax:.1f} m' if amin is not None and amax is not None else '—'
        self.cards['altitude'].set_value(altitude, _fmt(s.get('gps_altitude_range_m'), 1, ' m range'))
        self.cards['samples'].set_value(str(s.get('sample_count', 0)), 'Synchronized snapshots')
        self.cards['gps'].set_value(str(s.get('valid_gps_update_count', 0)), 'New valid GPS positions')

        tmin = s.get('min_temperature_c')
        tmax = s.get('max_temperature_c')
        tavg = s.get('average_temperature_c')
        temp_detail = f'{tmin:.1f}–{tmax:.1f} °C' if tmin is not None and tmax is not None else ''
        self.cards['temperature'].set_value(_fmt(tavg, 1, ' °C'), temp_detail)
        hum = _fmt(s.get('average_humidity_pct'), 1, '% RH')
        press = _fmt(s.get('average_pressure_hpa'), 1, ' hPa')
        self.cards['environment'].set_value(hum, f'{press} average pressure')

        md = session.metadata
        self.session_info.setText(
            f"<b>Session:</b> {session.session_id}<br>"
            f"<b>Device:</b> {md.get('device_name', '—')}<br>"
            f"<b>Firmware:</b> {md.get('firmware_version', '—')}<br>"
            f"<b>Schema:</b> {md.get('schema_version', '—')}<br>"
            f"<b>Start UTC:</b> {md.get('start_time_utc', '—')}<br>"
            f"<b>Log interval:</b> {md.get('log_interval_ms', '—')} ms"
        )

        report = session.validation
        if report.ok:
            self.validation_status.setObjectName('GoodStatus')
            self.validation_status.setText(
                f'✓ Session passed validation\n\n'
                f'{len(report.warnings)} warning(s) · {len(report.errors)} error(s)\n'
                f'{len(session.waypoints)} waypoint(s) · {len(session.events)} event(s)'
            )
        else:
            self.validation_status.setObjectName('WarningStatus')
            self.validation_status.setText(
                f'Validation failed\n\n{len(report.errors)} error(s) · {len(report.warnings)} warning(s)'
            )
        self.validation_status.style().unpolish(self.validation_status)
        self.validation_status.style().polish(self.validation_status)

        columns = ['sample_id', 'timestamp_utc', 'latitude_deg', 'longitude_deg', 'gps_altitude_m', 'temperature_c', 'heading_deg']
        df = session.samples.tail(12)
        self.preview_table.setRowCount(len(df))
        for r, (_, row) in enumerate(df.iterrows()):
            values = []
            for col in columns:
                value = row.get(col)
                if col == 'timestamp_utc' and pd.notna(value):
                    value = value.strftime('%H:%M:%S')
                elif col in {'latitude_deg', 'longitude_deg'} and pd.notna(value):
                    value = f'{float(value):.6f}'
                elif col in {'gps_altitude_m', 'temperature_c', 'heading_deg'} and pd.notna(value):
                    value = f'{float(value):.2f}'
                elif pd.isna(value):
                    value = ''
                values.append(str(value))
            for c, value in enumerate(values):
                self.preview_table.setItem(r, c, QTableWidgetItem(value))
        self.preview_table.resizeColumnsToContents()


class WaypointsEventsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 24)
        root.setSpacing(16)

        title = QLabel('Waypoints & Events')
        title.setObjectName('PageTitle')
        subtitle = QLabel('Recorded markers and session events')
        subtitle.setObjectName('PageSubtitle')
        root.addWidget(title)
        root.addWidget(subtitle)

        wp_panel = Panel('Waypoints')
        self.wp_table = QTableWidget()
        self.wp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.wp_table.setAlternatingRowColors(True)
        self.wp_table.verticalHeader().setVisible(False)
        wp_panel.outer.addWidget(self.wp_table)
        root.addWidget(wp_panel, 1)

        ev_panel = Panel('Events')
        self.ev_table = QTableWidget()
        self.ev_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ev_table.setAlternatingRowColors(True)
        self.ev_table.verticalHeader().setVisible(False)
        ev_panel.outer.addWidget(self.ev_table)
        root.addWidget(ev_panel, 1)

    @staticmethod
    def _fill(table: QTableWidget, df: pd.DataFrame, columns: list[str]):
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(df))
        for r, (_, row) in enumerate(df.iterrows()):
            for c, col in enumerate(columns):
                value = row.get(col, '')
                if col == 'timestamp_utc' and pd.notna(value):
                    value = value.strftime('%H:%M:%S')
                elif pd.isna(value):
                    value = ''
                table.setItem(r, c, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)

    def set_session(self, session):
        self._fill(self.wp_table, session.waypoints, [
            'waypoint_id', 'timestamp_utc', 'latitude_deg', 'longitude_deg', 'gps_altitude_m', 'heading_deg', 'label', 'note'
        ])
        self._fill(self.ev_table, session.events, [
            'event_id', 'timestamp_utc', 'event_type', 'value', 'note'
        ])


class PlaceholderPage(QWidget):
    def __init__(self, title_text: str, subtitle_text: str, icon_text: str, next_text: str):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 24)
        title = QLabel(title_text)
        title.setObjectName('PageTitle')
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName('PageSubtitle')
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addStretch(1)

        center = QFrame()
        center.setObjectName('Panel')
        center.setMaximumWidth(640)
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(38, 38, 38, 38)
        center_layout.setAlignment(Qt.AlignCenter)
        icon = QLabel(icon_text)
        icon.setObjectName('PlaceholderIcon')
        icon.setAlignment(Qt.AlignCenter)
        msg = QLabel(next_text)
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setObjectName('Muted')
        center_layout.addWidget(icon)
        center_layout.addSpacing(12)
        center_layout.addWidget(msg)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(center)
        row.addStretch(1)
        root.addLayout(row)
        root.addStretch(2)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('About GeoTracker Studio')
        self.setModal(True)
        self.setMinimumWidth(470)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(14)

        header = QHBoxLayout()
        mark = QLabel()
        mark.setFixedSize(58, 58)
        mark_path = resource_path('assets/geotracker_studio.png')
        if mark_path.exists():
            pix = QPixmap(str(mark_path))
            mark.setPixmap(pix.scaled(58, 58, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header.addWidget(mark, 0, Qt.AlignTop)

        title_col = QVBoxLayout()
        title = QLabel('<span style="color:#58a6ff">Geo</span><span style="color:#f0f6fc">Tracker</span> Studio')
        title.setObjectName('AboutTitle')
        title.setTextFormat(Qt.RichText)
        subtitle = QLabel('Version 1.0.0 · Field-data visualization and analysis')
        subtitle.setObjectName('PageSubtitle')
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col, 1)
        root.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName('Divider')
        root.addWidget(line)

        description = QLabel(
            'GeoTracker Studio is the desktop companion for GeoTracker v1.0. '
            'It imports recorded sessions, reconstructs 2D/3D routes, synchronizes '
            'sensor measurements with position, and exports geographic data to KML and GPX.'
        )
        description.setWordWrap(True)
        description.setObjectName('AboutBody')
        root.addWidget(description)

        details = QLabel(
            '<b>Core formats:</b> GeoTracker CSV · KML · GPX<br>'
            '<b>Mapping:</b> OpenStreetMap basemap support<br>'
            '<b>Runtime:</b> Python / Qt / OpenGL<br><br>'
            '<span style="color:#8b949e">Map data © OpenStreetMap contributors.</span>'
        )
        details.setTextFormat(Qt.RichText)
        details.setWordWrap(True)
        root.addWidget(details)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self, startup_session: Path | None = None):
        super().__init__()
        self.session = None
        self.selection_controller = SelectionController()
        self.setWindowTitle('GeoTracker Studio v1.0')
        self.resize(1380, 860)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(APP_QSS)
        self._build_menus()

        shell = QWidget()
        self.setCentralWidget(shell)
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName('Sidebar')
        sidebar.setFixedWidth(235)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 22, 18, 18)
        side.setSpacing(8)

        # Refined product identity: vector-style route/pin mark plus a crisp
        # text lockup. The mark is also used as the packaged Windows icon.
        brand_panel = QFrame()
        brand_panel.setObjectName('BrandPanel')
        brand_layout = QHBoxLayout(brand_panel)
        brand_layout.setContentsMargins(0, 0, 0, 16)
        brand_layout.setSpacing(11)

        mark = QLabel()
        mark.setObjectName('BrandMark')
        mark.setFixedSize(42, 42)
        mark_path = resource_path('assets/geotracker_studio.png')
        if mark_path.exists():
            pix = QPixmap(str(mark_path))
            mark.setPixmap(pix.scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand_layout.addWidget(mark, 0, Qt.AlignTop)

        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 0, 0, 0)
        brand_text.setSpacing(2)
        brand = QLabel('<span style="color:#58a6ff">Geo</span><span style="color:#f0f6fc">Tracker</span>')
        brand.setObjectName('Brand')
        brand.setTextFormat(Qt.RichText)
        brand_text.addWidget(brand)

        subrow = QHBoxLayout()
        subrow.setContentsMargins(0, 0, 0, 0)
        subrow.setSpacing(7)
        brand_sub = QLabel('STUDIO')
        brand_sub.setObjectName('BrandSub')
        version = QLabel('v1.0')
        version.setObjectName('VersionBadge')
        subrow.addWidget(brand_sub)
        subrow.addWidget(version)
        subrow.addStretch(1)
        brand_text.addLayout(subrow)
        brand_layout.addLayout(brand_text, 1)
        side.addWidget(brand_panel)
        side.addSpacing(10)

        section = QLabel('WORKSPACE')
        section.setObjectName('SidebarSection')
        side.addWidget(section)

        self.nav_buttons = []
        nav = [
            ('Overview', 0, 'nav_overview.svg'),
            ('2D Map', 1, 'nav_map.svg'),
            ('Data Graphs', 2, 'nav_graph.svg'),
            ('Waypoints & Events', 3, 'nav_waypoint.svg'),
            ('3D Route', 4, 'nav_3d.svg'),
            ('Export', 5, 'nav_export.svg'),
        ]
        for text, index, icon_name in nav:
            btn = QPushButton(text)
            btn.setObjectName('NavButton')
            btn.setCheckable(True)
            icon_path = resource_path(f'assets/{icon_name}')
            if icon_path.exists():
                btn.setIcon(QIcon(str(icon_path)))
                btn.setIconSize(QSize(18, 18))
            btn.clicked.connect(lambda checked=False, i=index: self.select_page(i))
            side.addWidget(btn)
            self.nav_buttons.append(btn)

        side.addStretch(1)
        session_section = QLabel('SESSION')
        session_section.setObjectName('SidebarSection')
        side.addWidget(session_section)
        self.session_mode_badge = QLabel('DEMO DATA')
        self.session_mode_badge.setObjectName('DemoBadge')
        self.session_mode_badge.hide()
        side.addWidget(self.session_mode_badge, 0, Qt.AlignLeft)
        self.session_label = QLabel('No session loaded')
        self.session_label.setObjectName('Muted')
        self.session_label.setWordWrap(True)
        side.addWidget(self.session_label)

        open_btn = QPushButton('Open session')
        open_btn.setObjectName('PrimaryButton')
        open_btn.clicked.connect(self.open_session_dialog)
        side.addWidget(open_btn)

        self.pages = QStackedWidget()
        self.overview_page = OverviewPage()
        self.overview_page.openSessionRequested.connect(self.open_session_dialog)
        self.map_page = RouteMapPage(self.selection_controller)
        self.graphs_page = DataGraphsPage(self.selection_controller)
        self.waypoints_page = WaypointsEventsPage()
        self.route3d_page = Route3DPage(self.selection_controller)
        self.export_page = ExportPage()
        self.export_page.exportCompleted.connect(self.statusBar().showMessage)
        for page in [self.overview_page, self.map_page, self.graphs_page, self.waypoints_page, self.route3d_page, self.export_page]:
            self.pages.addWidget(page)

        shell_layout.addWidget(sidebar)
        shell_layout.addWidget(self.pages, 1)
        self.statusBar().showMessage('GeoTracker Studio ready')
        self.select_page(0)

        if startup_session:
            self.load_session_path(startup_session)


    def _build_menus(self):
        file_menu = self.menuBar().addMenu('&File')
        open_action = QAction('Open session…', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_session_dialog)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu('&Help')
        about_action = QAction('About GeoTracker Studio', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_about_dialog(self):
        AboutDialog(self).exec()

    def select_page(self, index: int):
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def open_session_dialog(self):
        directory = QFileDialog.getExistingDirectory(self, 'Open GeoTracker session folder')
        if directory:
            self.load_session_path(directory)

    def load_session_path(self, path: str | Path):
        try:
            session = load_session(path)
        except GeoTrackerParseError as exc:
            QMessageBox.critical(self, 'Could not open session', str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, 'Unexpected error', f'Could not load session:\n{exc}')
            return

        self.session = session
        is_demo = (
            str(session.metadata.get('firmware_version', '')).lower().endswith('-demo')
            or str(session.session_id).upper().endswith('_DEMO')
        )
        self.overview_page.set_demo_state(is_demo)
        self.session_mode_badge.setVisible(is_demo)
        self.setWindowTitle('GeoTracker Studio v1.0' + (' — Demo Session' if is_demo else ''))
        self.overview_page.set_session(session)
        self.map_page.set_session(session)
        self.graphs_page.set_session(session)
        self.waypoints_page.set_session(session)
        self.route3d_page.set_session(session)
        self.export_page.set_session(session)
        self.session_label.setText(f'{session.session_id}\n{len(session.samples)} samples')

        self.selection_controller.clear()
        valid = session.gps_updates
        if not valid.empty:
            self.selection_controller.select(int(valid.iloc[0]['sample_id']), force=True)
        elif not session.samples.empty:
            self.selection_controller.select(int(session.samples.iloc[0]['sample_id']), force=True)

        if session.validation.ok:
            demo_note = ' · DEMO DATA' if is_demo else ''
            self.statusBar().showMessage(
                f'Loaded {session.session_id} · {len(session.samples)} samples · validation passed{demo_note}'
            )
        else:
            self.statusBar().showMessage(
                f'Loaded {session.session_id} with {len(session.validation.errors)} validation error(s)'
            )
