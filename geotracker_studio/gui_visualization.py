from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtCore import QObject, Qt, Signal, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QVector3D
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .gui_basemap import BasemapLoadError, load_session_basemap
from .visualization_data import (
    METRICS,
    METRICS_BY_LABEL,
    OVERLAYS,
    OVERLAYS_BY_LABEL,
    local_projection_reference,
    metric_values,
    overlay_values,
    project_latlon_to_local_m,
    robust_value_range,
    route_3d_data,
    contiguous_valid_runs,
    x_axis_values,
)


GRADIENT_STOPS = (
    (0.00, (46, 107, 230)),
    (0.25, (32, 190, 208)),
    (0.50, (72, 199, 116)),
    (0.75, (235, 190, 63)),
    (1.00, (235, 77, 75)),
)


class SelectionController(QObject):
    sampleSelected = Signal(int)

    def __init__(self):
        super().__init__()
        self._sample_id: int | None = None

    @property
    def sample_id(self) -> int | None:
        return self._sample_id

    def clear(self):
        self._sample_id = None

    def select(self, sample_id: int, force: bool = False):
        sample_id = int(sample_id)
        if force or self._sample_id != sample_id:
            self._sample_id = sample_id
            self.sampleSelected.emit(sample_id)


def _configure_plot(plot: pg.PlotWidget):
    plot.setBackground('#10171f')
    plot.showGrid(x=True, y=True, alpha=0.16)
    plot.getPlotItem().getAxis('left').setTextPen(pg.mkPen('#93a4b5'))
    plot.getPlotItem().getAxis('bottom').setTextPen(pg.mkPen('#93a4b5'))
    plot.getPlotItem().getAxis('left').setPen(pg.mkPen('#344454'))
    plot.getPlotItem().getAxis('bottom').setPen(pg.mkPen('#344454'))
    plot.getPlotItem().getViewBox().setMouseMode(pg.ViewBox.PanMode)


def _sample_row(session, sample_id: int):
    rows = session.samples[session.samples['sample_id'] == sample_id]
    if rows.empty:
        return None
    return rows.iloc[0]


def _fmt_num(value, digits=2, suffix=''):
    try:
        if pd.isna(value):
            return '—'
        return f'{float(value):.{digits}f}{suffix}'
    except Exception:
        return '—'


def _interpolate_color(t: float) -> QColor:
    t = float(np.clip(t, 0.0, 1.0))
    for i in range(1, len(GRADIENT_STOPS)):
        p0, c0 = GRADIENT_STOPS[i - 1]
        p1, c1 = GRADIENT_STOPS[i]
        if t <= p1:
            f = (t - p0) / (p1 - p0) if p1 > p0 else 0.0
            rgb = [round(c0[j] + f * (c1[j] - c0[j])) for j in range(3)]
            return QColor(*rgb)
    return QColor(*GRADIENT_STOPS[-1][1])


def _value_color(value: float, lo: float, hi: float, reverse: bool = False) -> QColor:
    if not np.isfinite(value):
        return QColor('#687888')
    t = (float(value) - lo) / (hi - lo)
    if reverse:
        t = 1.0 - t
    return _interpolate_color(t)


class GradientBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(12)
        self.setMinimumWidth(180)

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        for pos, rgb in GRADIENT_STOPS:
            gradient.setColorAt(pos, QColor(*rgb))
        painter.fillRect(self.rect(), gradient)


class OverlayLegend(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName('Panel')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 8)
        layout.setSpacing(4)
        self.title = QLabel('Normal route')
        self.title.setObjectName('Muted')
        self.bar = GradientBar()
        labels = QHBoxLayout()
        self.minimum = QLabel('')
        self.minimum.setObjectName('Muted')
        self.maximum = QLabel('')
        self.maximum.setObjectName('Muted')
        labels.addWidget(self.minimum)
        labels.addStretch(1)
        labels.addWidget(self.maximum)
        layout.addWidget(self.title)
        layout.addWidget(self.bar)
        layout.addLayout(labels)
        self.hide()

    def set_range(self, title: str, lo: float, hi: float, unit: str, reversed_scale: bool = False):
        self.title.setText(title + (' · better →' if reversed_scale else ''))
        self.minimum.setText(f'{lo:.2f} {unit}'.strip())
        self.maximum.setText(f'{hi:.2f} {unit}'.strip())
        self.show()


class InspectorPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName('Panel')
        self.setMinimumWidth(260)
        self.setMaximumWidth(340)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        title = QLabel('Selected sample')
        title.setObjectName('PanelTitle')
        self.sample_label = QLabel('Click the route or a graph to inspect a sample.')
        self.sample_label.setObjectName('Muted')
        self.sample_label.setWordWrap(True)

        self.details = QLabel('')
        self.details.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.details.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.sample_label)
        layout.addSpacing(6)
        layout.addWidget(self.details)
        layout.addStretch(1)

    def set_sample(self, session, sample_id: int):
        row = _sample_row(session, sample_id)
        if row is None:
            return

        timestamp = row.get('timestamp_utc')
        if pd.notna(timestamp):
            timestamp = timestamp.strftime('%H:%M:%S UTC')
        else:
            timestamp = '—'

        self.sample_label.setText(f'Sample {sample_id} · {timestamp}')
        self.details.setText(
            f"<b>Position</b><br>"
            f"Lat: {_fmt_num(row.get('latitude_deg'), 6)}<br>"
            f"Lon: {_fmt_num(row.get('longitude_deg'), 6)}<br>"
            f"Altitude: {_fmt_num(row.get('gps_altitude_m'), 1, ' m')}<br>"
            f"Speed: {_fmt_num(row.get('speed_mps'), 2, ' m/s')}<br>"
            f"GPS: {_fmt_num(row.get('satellites'), 0, ' sat')} · HDOP {_fmt_num(row.get('hdop'), 2)}<br><br>"
            f"<b>Environment</b><br>"
            f"Temperature: {_fmt_num(row.get('temperature_c'), 1, ' °C')}<br>"
            f"Humidity: {_fmt_num(row.get('humidity_pct'), 1, '% RH')}<br>"
            f"Pressure: {_fmt_num(row.get('pressure_hpa'), 1, ' hPa')}<br><br>"
            f"<b>Orientation</b><br>"
            f"Heading: {_fmt_num(row.get('heading_deg'), 1, '°')}<br>"
            f"Pitch: {_fmt_num(row.get('pitch_deg'), 1, '°')}<br>"
            f"Roll: {_fmt_num(row.get('roll_deg'), 1, '°')}"
        )


class RouteMapPage(QWidget):
    def __init__(self, controller: SelectionController):
        super().__init__()
        self.controller = controller
        self.session = None
        self._all_ids = np.array([], dtype=int)
        self._gps_valid = np.array([], dtype=bool)
        self._x = np.array([], dtype=float)
        self._y = np.array([], dtype=float)
        self._lat0 = 0.0
        self._lon0 = 0.0
        self._route_items = []
        self._basemap_item = None
        self._basemap_raster = None

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 24)
        root.setSpacing(12)

        title = QLabel('2D Map')
        title.setObjectName('PageTitle')
        subtitle = QLabel('Local metric route view · overlays, hover inspection, and synchronized sample selection')
        subtitle.setObjectName('PageSubtitle')
        root.addWidget(title)
        root.addWidget(subtitle)

        # Keep status and map controls on separate rows so the toolbar remains
        # readable on ordinary laptop/desktop window widths.
        status_row = QHBoxLayout()
        self.route_status = QLabel('No session loaded')
        self.route_status.setObjectName('Muted')
        status_row.addWidget(self.route_status)
        status_row.addStretch(1)
        root.addLayout(status_row)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        map_label = QLabel('Map layer')
        map_label.setObjectName('Muted')
        self.basemap_combo = QComboBox()
        self.basemap_combo.setObjectName('MapCombo')
        self.basemap_combo.addItems(['No basemap', 'OpenStreetMap'])
        self.basemap_combo.currentTextChanged.connect(self._basemap_changed)
        toolbar.addWidget(map_label)
        toolbar.addWidget(self.basemap_combo)

        opacity_label = QLabel('Map opacity')
        opacity_label.setObjectName('Muted')
        self.basemap_opacity = QSlider(Qt.Horizontal)
        self.basemap_opacity.setRange(25, 100)
        self.basemap_opacity.setValue(72)
        self.basemap_opacity.setFixedWidth(110)
        self.basemap_opacity.valueChanged.connect(self._basemap_opacity_changed)
        toolbar.addSpacing(6)
        toolbar.addWidget(opacity_label)
        toolbar.addWidget(self.basemap_opacity)

        toolbar.addStretch(1)
        overlay_label = QLabel('Route display')
        overlay_label.setObjectName('Muted')
        self.overlay_combo = QComboBox()
        self.overlay_combo.setObjectName('OverlayCombo')
        for overlay in OVERLAYS:
            self.overlay_combo.addItem(overlay.label)
        self.overlay_combo.currentTextChanged.connect(self._render_route)
        toolbar.addWidget(overlay_label)
        toolbar.addWidget(self.overlay_combo)
        reset = QPushButton('Fit route')
        reset.setObjectName('SecondaryButton')
        reset.clicked.connect(self.fit_route)
        toolbar.addWidget(reset)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        self.plot = pg.PlotWidget()
        _configure_plot(self.plot)
        self.plot.setLabel('bottom', 'East / West from session center (m)')
        self.plot.setLabel('left', 'North / South from session center (m)')
        self.plot.getPlotItem().getViewBox().setAspectLocked(True, ratio=1)
        self.plot.setToolTip('Mouse wheel: zoom · drag: pan · click: select nearest GPS sample')
        left_layout.addWidget(self.plot, 1)
        self.map_attribution = QLabel('Basemap off')
        self.map_attribution.setObjectName('Muted')
        self.map_attribution.setOpenExternalLinks(True)
        left_layout.addWidget(self.map_attribution)
        self.legend = OverlayLegend()
        left_layout.addWidget(self.legend)

        self.inspector = InspectorPanel()
        splitter.addWidget(left)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([900, 280])
        root.addWidget(splitter, 1)

        self.selection_item = pg.ScatterPlotItem([], [], symbol='o', size=18,
            pen=pg.mkPen('#ffffff', width=2.3), brush=pg.mkBrush(88, 166, 255, 110))
        self.hover_item = pg.ScatterPlotItem([], [], symbol='o', size=11,
            pen=pg.mkPen('#f0f6fc', width=1.5), brush=pg.mkBrush(240, 246, 252, 30))
        self.hover_text = pg.TextItem('', color='#c9d1d9', anchor=(0, 1))

        self.plot.scene().sigMouseClicked.connect(self._plot_clicked)
        self._mouse_proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=30, slot=self._mouse_moved)
        self.controller.sampleSelected.connect(self._selection_changed)

    def set_session(self, session):
        self.session = session
        samples = session.samples
        lat = pd.to_numeric(samples['latitude_deg'], errors='coerce').to_numpy(dtype=float)
        lon = pd.to_numeric(samples['longitude_deg'], errors='coerce').to_numpy(dtype=float)
        self._all_ids = pd.to_numeric(samples['sample_id'], errors='coerce').fillna(-1).astype(int).to_numpy()
        valid_flag = samples['gps_valid'].fillna(False).astype(bool).to_numpy()
        self._gps_valid = valid_flag & np.isfinite(lat) & np.isfinite(lon)
        self._lat0, self._lon0 = local_projection_reference(samples)
        self._x, self._y = project_latlon_to_local_m(lat, lon, self._lat0, self._lon0)

        self.route_status.setText(
            f'{int(self._gps_valid.sum())} valid GPS points · {len(session.waypoints)} waypoint(s) · '
            f'{len(session.events)} event(s) · local meter projection'
        )
        self._render_route()
        if self.basemap_combo.currentText() != 'No basemap':
            self._load_basemap()
        self.fit_route()

    def _remove_basemap(self):
        if self._basemap_item is not None:
            try:
                self.plot.removeItem(self._basemap_item)
            except Exception:
                pass
        self._basemap_item = None
        self._basemap_raster = None

    def _basemap_changed(self, text: str):
        if text == 'No basemap':
            self._remove_basemap()
            self.map_attribution.setText('Basemap off')
            return
        self._load_basemap()

    def _load_basemap(self):
        if self.session is None:
            return
        self._remove_basemap()
        self.map_attribution.setText('Loading OpenStreetMap tiles for the current route…')
        try:
            raster = load_session_basemap(self.session.samples, self._lat0, self._lon0, 'osm')
        except BasemapLoadError as exc:
            self.map_attribution.setText(f'Basemap unavailable: {exc}')
            return

        # Image rows arrive north-at-top; flip vertically so local +Y remains north.
        image = np.flipud(raster.rgba).copy()
        item = pg.ImageItem(image=image, axisOrder='row-major')
        item.setRect(QRectF(raster.x_min_m, raster.y_min_m, raster.width_m, raster.height_m))
        item.setOpacity(self.basemap_opacity.value() / 100.0)
        item.setZValue(-100)
        self.plot.addItem(item)
        self._basemap_item = item
        self._basemap_raster = raster
        failed = f' · {raster.failures} tile(s) unavailable' if raster.failures else ''
        self.map_attribution.setText(
            f'<a href="https://www.openstreetmap.org/copyright">{raster.attribution}</a>'
            f' · zoom {raster.zoom} · {raster.tile_count} cached/view tiles{failed}'
        )

    def _basemap_opacity_changed(self, value: int):
        if self._basemap_item is not None:
            self._basemap_item.setOpacity(value / 100.0)

    def _clear_route_items(self):
        for item in self._route_items:
            try:
                self.plot.removeItem(item)
            except Exception:
                pass
        self._route_items = []
        self.plot.removeItem(self.selection_item)
        self.plot.removeItem(self.hover_item)
        self.plot.removeItem(self.hover_text)

    def _add_item(self, item):
        self.plot.addItem(item)
        self._route_items.append(item)
        return item

    def _render_route(self):
        if self.session is None:
            return
        self._clear_route_items()
        definition = OVERLAYS_BY_LABEL[self.overlay_combo.currentText()]

        if definition.column is None:
            route_x = np.where(self._gps_valid, self._x, np.nan)
            route_y = np.where(self._gps_valid, self._y, np.nan)
            self._add_item(self.plot.plot(route_x, route_y, pen=pg.mkPen('#58a6ff', width=2.3), connect='finite'))
            self.legend.hide()
        else:
            values = overlay_values(self.session.samples, definition)
            value_range = robust_value_range(values[self._gps_valid])
            self._add_item(self.plot.plot(
                np.where(self._gps_valid, self._x, np.nan),
                np.where(self._gps_valid, self._y, np.nan),
                pen=pg.mkPen('#314457', width=4.0), connect='finite'))
            if value_range:
                lo, hi = value_range
                for i in range(1, len(self._x)):
                    if not (self._gps_valid[i - 1] and self._gps_valid[i]):
                        continue
                    v1, v2 = values[i - 1], values[i]
                    if not (np.isfinite(v1) and np.isfinite(v2)):
                        continue
                    color = _value_color((v1 + v2) / 2.0, lo, hi, definition.reverse_scale)
                    self._add_item(pg.PlotCurveItem(
                        [self._x[i - 1], self._x[i]], [self._y[i - 1], self._y[i]],
                        pen=pg.mkPen(color, width=4.2)))
                self.legend.set_range(definition.label, lo, hi, definition.unit, definition.reverse_scale)
            else:
                self.legend.hide()

        valid_idx = np.where(self._gps_valid)[0]
        if len(valid_idx):
            first, last = valid_idx[0], valid_idx[-1]
            self._add_item(pg.ScatterPlotItem([self._x[first]], [self._y[first]], symbol='o', size=13,
                pen=pg.mkPen('#3fb950', width=2), brush=pg.mkBrush('#238636')))
            self._add_item(pg.ScatterPlotItem([self._x[last]], [self._y[last]], symbol='s', size=13,
                pen=pg.mkPen('#f85149', width=2), brush=pg.mkBrush('#da3633')))

        self._render_waypoints_events()
        self.plot.addItem(self.selection_item)
        self.plot.addItem(self.hover_item)
        self.plot.addItem(self.hover_text)
        if self.controller.sample_id is not None:
            self._selection_changed(self.controller.sample_id)

    def _project_point(self, lat, lon):
        try:
            if pd.isna(lat) or pd.isna(lon):
                return None
            x, y = project_latlon_to_local_m([float(lat)], [float(lon)], self._lat0, self._lon0)
            return float(x[0]), float(y[0])
        except Exception:
            return None

    def _render_waypoints_events(self):
        if not self.session.waypoints.empty:
            spots = []
            for _, row in self.session.waypoints.iterrows():
                pos = self._project_point(row.get('latitude_deg'), row.get('longitude_deg'))
                if pos:
                    spots.append({'pos': pos, 'data': int(row['source_sample_id']), 'symbol': 't', 'size': 15})
            if spots:
                item = pg.ScatterPlotItem(spots=spots, pen=pg.mkPen('#d29922', width=2),
                                          brush=pg.mkBrush('#9e6a03'))
                item.sigClicked.connect(self._marker_clicked)
                self._add_item(item)

        if not self.session.events.empty:
            events = self.session.events[~self.session.events['event_type'].isin(['SESSION_START','SESSION_END','WAYPOINT_CREATED'])]
            spots = []
            for _, row in events.iterrows():
                pos = self._project_point(row.get('latitude_deg'), row.get('longitude_deg'))
                if pos:
                    spots.append({'pos': pos, 'data': int(row['source_sample_id']), 'symbol': 'x', 'size': 13})
            if spots:
                item = pg.ScatterPlotItem(spots=spots, pen=pg.mkPen('#bc8cff', width=2), brush=None)
                item.sigClicked.connect(self._marker_clicked)
                self._add_item(item)

    def fit_route(self):
        if self._gps_valid.any():
            self.plot.enableAutoRange()
            self.plot.autoRange(padding=0.10)

    def _nearest_valid_index(self, x: float, y: float):
        valid_idx = np.where(self._gps_valid & np.isfinite(self._x) & np.isfinite(self._y))[0]
        if not len(valid_idx):
            return None
        d2 = (self._x[valid_idx] - x) ** 2 + (self._y[valid_idx] - y) ** 2
        return int(valid_idx[int(np.argmin(d2))])

    def _marker_clicked(self, item, points, event):
        if points and points[0].data() is not None:
            self.controller.select(int(points[0].data()))

    def _plot_clicked(self, event):
        if self.session is None or event.button() != Qt.LeftButton:
            return
        vb = self.plot.getPlotItem().vb
        pos = vb.mapSceneToView(event.scenePos())
        i = self._nearest_valid_index(float(pos.x()), float(pos.y()))
        if i is not None:
            self.controller.select(int(self._all_ids[i]))

    def _mouse_moved(self, event):
        if self.session is None or not self.plot.sceneBoundingRect().contains(event):
            self.hover_item.setData([], [])
            self.hover_text.setText('')
            return
        vb = self.plot.getPlotItem().vb
        pos = vb.mapSceneToView(event)
        i = self._nearest_valid_index(float(pos.x()), float(pos.y()))
        if i is None:
            return
        self.hover_item.setData([self._x[i]], [self._y[i]])
        row = self.session.samples.iloc[i]
        self.hover_text.setPos(float(self._x[i]), float(self._y[i]))
        self.hover_text.setText(
            f"Sample {int(self._all_ids[i])}  |  "
            f"{_fmt_num(row.get('gps_altitude_m'), 1, ' m')}  |  "
            f"{_fmt_num(row.get('temperature_c'), 1, ' °C')}"
        )

    def _selection_changed(self, sample_id: int):
        if self.session is None:
            return
        matches = np.where(self._all_ids == int(sample_id))[0]
        if not len(matches):
            return
        i = int(matches[0])
        if self._gps_valid[i]:
            self.selection_item.setData([float(self._x[i])], [float(self._y[i])])
        else:
            self.selection_item.setData([], [])
        self.inspector.set_sample(self.session, sample_id)


class MetricPlotCard(QFrame):
    def __init__(self, controller: SelectionController, default_metric: str):
        super().__init__()
        self.controller = controller
        self.session = None
        self.x_mode = 'Elapsed time (s)'
        self._x = np.array([], dtype=float)
        self._y = np.array([], dtype=float)
        self._ids = np.array([], dtype=int)
        self._definition = METRICS_BY_LABEL[default_metric]

        self.setObjectName('Panel')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        metric_label = QLabel('Metric')
        metric_label.setObjectName('Muted')
        self.metric_combo = QComboBox()
        for metric in METRICS:
            self.metric_combo.addItem(metric.label)
        self.metric_combo.setCurrentText(default_metric)
        self.metric_combo.currentTextChanged.connect(self.replot)
        header.addWidget(metric_label)
        header.addWidget(self.metric_combo)
        header.addStretch(1)
        self.hover_label = QLabel('Hover the graph to inspect values')
        self.hover_label.setObjectName('Muted')
        header.addWidget(self.hover_label)
        layout.addLayout(header)

        self.plot = pg.PlotWidget()
        _configure_plot(self.plot)
        self.plot.setMinimumHeight(230)
        layout.addWidget(self.plot, 1)

        self.curve = self.plot.plot([], [], pen=pg.mkPen('#58a6ff', width=2.0), connect='finite')
        self.selection_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#f0f6fc', width=1.4))
        self.hover_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#8b949e', width=1, style=Qt.DashLine))
        self.selection_item = pg.ScatterPlotItem([], [], symbol='o', size=12,
            pen=pg.mkPen('#ffffff', width=2), brush=pg.mkBrush('#1f6feb'))
        self.hover_item = pg.ScatterPlotItem([], [], symbol='o', size=9,
            pen=pg.mkPen('#c9d1d9', width=1), brush=pg.mkBrush(201, 209, 217, 50))
        self.plot.addItem(self.selection_line)
        self.plot.addItem(self.hover_line)
        self.plot.addItem(self.selection_item)
        self.plot.addItem(self.hover_item)
        self.selection_line.hide()
        self.hover_line.hide()

        self.plot.scene().sigMouseClicked.connect(self._plot_clicked)
        self._mouse_proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved, rateLimit=30, slot=self._mouse_moved)
        self.controller.sampleSelected.connect(self._selection_changed)

    def set_session(self, session):
        self.session = session
        self.replot()

    def set_x_mode(self, mode: str):
        self.x_mode = mode
        self.replot()

    def replot(self):
        if self.session is None:
            return
        self._definition = METRICS_BY_LABEL[self.metric_combo.currentText()]
        self._x, x_label = x_axis_values(self.session.samples, self.x_mode)
        self._y = metric_values(self.session.samples, self._definition)
        self._ids = pd.to_numeric(self.session.samples['sample_id'], errors='coerce').fillna(-1).astype(int).to_numpy()

        self.curve.setData(self._x, self._y, connect='finite')
        self.plot.setLabel('bottom', x_label)
        self.plot.setLabel('left', f'{self._definition.label} ({self._definition.unit})')
        self.plot.getPlotItem().setTitle(self._definition.label, color='#c9d1d9', size='11pt')
        self.plot.autoRange(padding=0.04)

        if self.controller.sample_id is not None:
            self._selection_changed(self.controller.sample_id)

    def _nearest_valid_index(self, x: float):
        finite = np.isfinite(self._x) & np.isfinite(self._y)
        if not finite.any():
            return None
        indices = np.where(finite)[0]
        return int(indices[int(np.argmin(np.abs(self._x[indices] - x)))])

    def _plot_clicked(self, event):
        if self.session is None or not len(self._x) or event.button() != Qt.LeftButton:
            return
        pos = self.plot.getPlotItem().vb.mapSceneToView(event.scenePos())
        i = self._nearest_valid_index(float(pos.x()))
        if i is not None:
            self.controller.select(int(self._ids[i]))

    def _mouse_moved(self, event):
        if self.session is None or not self.plot.sceneBoundingRect().contains(event):
            self.hover_line.hide()
            self.hover_item.setData([], [])
            return
        pos = self.plot.getPlotItem().vb.mapSceneToView(event)
        i = self._nearest_valid_index(float(pos.x()))
        if i is None:
            return
        self.hover_line.setPos(float(self._x[i]))
        self.hover_line.show()
        self.hover_item.setData([float(self._x[i])], [float(self._y[i])])
        self.hover_label.setText(
            f'Sample {int(self._ids[i])} · {_fmt_num(self._y[i], 2, " " + self._definition.unit)}'
        )

    def _selection_changed(self, sample_id: int):
        if self.session is None or not len(self._ids):
            return
        matches = np.where(self._ids == int(sample_id))[0]
        if not len(matches):
            return
        i = int(matches[0])
        if i < len(self._x) and np.isfinite(self._x[i]):
            self.selection_line.setPos(float(self._x[i]))
            self.selection_line.show()
            if np.isfinite(self._y[i]):
                self.selection_item.setData([float(self._x[i])], [float(self._y[i])])
            else:
                self.selection_item.setData([], [])
        else:
            self.selection_line.hide()
            self.selection_item.setData([], [])


class DataGraphsPage(QWidget):
    def __init__(self, controller: SelectionController):
        super().__init__()
        self.controller = controller
        self.session = None

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 24)
        root.setSpacing(12)

        title = QLabel('Data Graphs')
        title.setObjectName('PageTitle')
        subtitle = QLabel('Interactive sensor analysis · selection lines synchronize with the 2D route')
        subtitle.setObjectName('PageSubtitle')
        root.addWidget(title)
        root.addWidget(subtitle)

        controls = QHBoxLayout()
        axis_label = QLabel('Horizontal axis')
        axis_label.setObjectName('Muted')
        self.axis_combo = QComboBox()
        self.axis_combo.addItems(['Elapsed time (s)', 'Distance (m)', 'Sample ID'])
        self.axis_combo.currentTextChanged.connect(self._axis_changed)
        controls.addWidget(axis_label)
        controls.addWidget(self.axis_combo)
        controls.addStretch(1)
        hint = QLabel('Hover for values · click to select and synchronize')
        hint.setObjectName('Muted')
        controls.addWidget(hint)
        root.addLayout(controls)

        self.top_plot = MetricPlotCard(controller, 'GPS altitude')
        self.bottom_plot = MetricPlotCard(controller, 'Temperature')
        root.addWidget(self.top_plot, 1)
        root.addWidget(self.bottom_plot, 1)

        self.selection_summary = QLabel('No sample selected')
        self.selection_summary.setObjectName('Muted')
        root.addWidget(self.selection_summary)
        self.controller.sampleSelected.connect(self._selection_changed)

    def set_session(self, session):
        self.session = session
        self.top_plot.set_session(session)
        self.bottom_plot.set_session(session)

    def _axis_changed(self, mode: str):
        self.top_plot.set_x_mode(mode)
        self.bottom_plot.set_x_mode(mode)

    def _selection_changed(self, sample_id: int):
        if self.session is None:
            return
        row = _sample_row(self.session, sample_id)
        if row is None:
            return
        timestamp = row.get('timestamp_utc')
        time_text = timestamp.strftime('%H:%M:%S') if pd.notna(timestamp) else '—'
        self.selection_summary.setText(
            f'Selected sample {sample_id} · {time_text} · '
            f'altitude {_fmt_num(row.get("gps_altitude_m"), 1, " m")} · '
            f'temperature {_fmt_num(row.get("temperature_c"), 1, " °C")} · '
            f'heading {_fmt_num(row.get("heading_deg"), 1, "°")}'
        )

class Route3DPage(QWidget):
    """Interactive 3D reconstruction of the GeoTracker GPS path."""

    VERTICAL_SCALES = {
        '1×': 1.0,
        '2×': 2.0,
        '5×': 5.0,
        '10×': 10.0,
    }

    def __init__(self, controller: SelectionController):
        super().__init__()
        self.controller = controller
        self.session = None
        self.route = None
        self._route_items = []
        self._waypoint_item = None
        self._selection_item = None
        self._grid = None
        self._axis = None
        self._basemap_item = None
        self._basemap_raster = None

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 24)
        root.setSpacing(12)

        title = QLabel('3D Route')
        title.setObjectName('PageTitle')
        subtitle = QLabel('Metric GPS path reconstruction · altitude, sensor overlays, and synchronized sample selection')
        subtitle.setObjectName('PageSubtitle')
        root.addWidget(title)
        root.addWidget(subtitle)

        # 3D has more controls than the 2D page.  Use a status row plus two
        # compact control rows rather than forcing every widget into one line.
        status_row = QHBoxLayout()
        self.route_status = QLabel('No session loaded')
        self.route_status.setObjectName('Muted')
        status_row.addWidget(self.route_status)
        status_row.addStretch(1)
        root.addLayout(status_row)

        controls = QHBoxLayout()
        controls.setSpacing(10)

        map_label = QLabel('Map layer')
        map_label.setObjectName('Muted')
        self.basemap_combo = QComboBox()
        self.basemap_combo.setObjectName('MapCombo')
        self.basemap_combo.addItems(['No basemap', 'OpenStreetMap'])
        self.basemap_combo.currentTextChanged.connect(self._basemap_changed)
        controls.addWidget(map_label)
        controls.addWidget(self.basemap_combo)

        opacity_label = QLabel('Map opacity')
        opacity_label.setObjectName('Muted')
        self.basemap_opacity = QSlider(Qt.Horizontal)
        self.basemap_opacity.setRange(25, 100)
        self.basemap_opacity.setValue(82)
        self.basemap_opacity.setFixedWidth(110)
        self.basemap_opacity.valueChanged.connect(self._basemap_opacity_changed)
        controls.addSpacing(6)
        controls.addWidget(opacity_label)
        controls.addWidget(self.basemap_opacity)
        controls.addStretch(1)

        overlay_label = QLabel('Route display')
        overlay_label.setObjectName('Muted')
        self.overlay_combo = QComboBox()
        self.overlay_combo.setObjectName('OverlayCombo')
        for overlay in OVERLAYS:
            self.overlay_combo.addItem(overlay.label)
        self.overlay_combo.currentTextChanged.connect(self._render_scene)
        controls.addWidget(overlay_label)
        controls.addWidget(self.overlay_combo)
        root.addLayout(controls)

        view_controls = QHBoxLayout()
        view_controls.setSpacing(10)
        vertical_label = QLabel('Vertical scale')
        vertical_label.setObjectName('Muted')
        self.vertical_combo = QComboBox()
        self.vertical_combo.setObjectName('ScaleCombo')
        self.vertical_combo.addItems(list(self.VERTICAL_SCALES))
        self.vertical_combo.setCurrentText('5×')
        self.vertical_combo.currentTextChanged.connect(self._render_scene)
        view_controls.addWidget(vertical_label)
        view_controls.addWidget(self.vertical_combo)
        view_controls.addStretch(1)

        fit_btn = QPushButton('Fit view')
        fit_btn.setObjectName('SecondaryButton')
        fit_btn.clicked.connect(self.fit_view)
        top_btn = QPushButton('Top')
        top_btn.setObjectName('SecondaryButton')
        top_btn.clicked.connect(self.top_view)
        perspective_btn = QPushButton('Perspective')
        perspective_btn.setObjectName('SecondaryButton')
        perspective_btn.clicked.connect(self.perspective_view)
        view_controls.addWidget(fit_btn)
        view_controls.addWidget(top_btn)
        view_controls.addWidget(perspective_btn)
        root.addLayout(view_controls)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor(QColor('#10171f'))
        self.view.setMinimumHeight(500)
        self.view.opts['fov'] = 55
        left_layout.addWidget(self.view, 1)

        self.map_attribution = QLabel('Basemap off')
        self.map_attribution.setObjectName('Muted')
        self.map_attribution.setOpenExternalLinks(True)
        left_layout.addWidget(self.map_attribution)

        self.legend = OverlayLegend()
        left_layout.addWidget(self.legend)

        scrubber_panel = QFrame()
        scrubber_panel.setObjectName('Panel')
        scrub = QHBoxLayout(scrubber_panel)
        scrub.setContentsMargins(12, 8, 12, 8)
        scrub.setSpacing(10)
        prev_btn = QPushButton('◀')
        prev_btn.setObjectName('SecondaryButton')
        prev_btn.setFixedWidth(44)
        next_btn = QPushButton('▶')
        next_btn.setObjectName('SecondaryButton')
        next_btn.setFixedWidth(44)
        self.sample_slider = QSlider(Qt.Horizontal)
        self.sample_slider.setMinimum(0)
        self.sample_slider.setMaximum(0)
        self.sample_slider.valueChanged.connect(self._slider_changed)
        self.slider_label = QLabel('No sample selected')
        self.slider_label.setObjectName('Muted')
        self.slider_label.setMinimumWidth(170)
        prev_btn.clicked.connect(lambda: self.sample_slider.setValue(max(0, self.sample_slider.value() - 1)))
        next_btn.clicked.connect(lambda: self.sample_slider.setValue(min(self.sample_slider.maximum(), self.sample_slider.value() + 1)))
        scrub.addWidget(prev_btn)
        scrub.addWidget(self.sample_slider, 1)
        scrub.addWidget(next_btn)
        scrub.addWidget(self.slider_label)
        left_layout.addWidget(scrubber_panel)

        self.inspector = InspectorPanel()
        splitter.addWidget(left)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([900, 300])
        root.addWidget(splitter, 1)

        self.controller.sampleSelected.connect(self._selection_changed)

    def set_session(self, session):
        self.session = session
        self.route = route_3d_data(session.samples)
        self.sample_slider.blockSignals(True)
        self.sample_slider.setMaximum(max(len(session.samples) - 1, 0))
        self.sample_slider.blockSignals(False)

        valid_count = int(self.route.valid.sum())
        if valid_count:
            alt = self.route.altitude_m[self.route.valid]
            alt_range = float(np.nanmax(alt) - np.nanmin(alt))
            xspan = float(np.nanmax(self.route.x_m[self.route.valid]) - np.nanmin(self.route.x_m[self.route.valid]))
            yspan = float(np.nanmax(self.route.y_m[self.route.valid]) - np.nanmin(self.route.y_m[self.route.valid]))
            self.route_status.setText(
                f'{valid_count} GPS/altitude points · {xspan:.1f} × {yspan:.1f} m footprint · {alt_range:.1f} m altitude range'
            )
        else:
            self.route_status.setText('No valid GPS altitude data')

        self._render_scene()
        if self.basemap_combo.currentText() != 'No basemap':
            self._load_basemap()
        self.fit_view()
        if self.controller.sample_id is not None:
            self._selection_changed(self.controller.sample_id)

    def _basemap_changed(self, text: str):
        if text == 'No basemap':
            self._basemap_raster = None
            self.map_attribution.setText('Basemap off')
            self._render_scene()
            return
        self._load_basemap()

    def _load_basemap(self):
        if self.session is None or self.route is None:
            return
        self.map_attribution.setText('Loading OpenStreetMap tiles for the current route…')
        try:
            raster = load_session_basemap(
                self.session.samples,
                self.route.lat0,
                self.route.lon0,
                'osm',
            )
        except BasemapLoadError as exc:
            self._basemap_raster = None
            self.map_attribution.setText(f'Basemap unavailable: {exc}')
            self._render_scene()
            return
        self._basemap_raster = raster
        failed = f' · {raster.failures} tile(s) unavailable' if raster.failures else ''
        self.map_attribution.setText(
            f'<a href="https://www.openstreetmap.org/copyright">{raster.attribution}</a>'
            f' · zoom {raster.zoom} · {raster.tile_count} cached/view tiles{failed}'
        )
        self._render_scene()

    def _basemap_opacity_changed(self, value: int):
        if self._basemap_raster is not None:
            self._render_scene()

    def _clear_scene(self):
        for item in self._route_items:
            try:
                self.view.removeItem(item)
            except Exception:
                pass
        self._route_items = []
        for item in [self._waypoint_item, self._selection_item, self._grid, self._axis, self._basemap_item]:
            if item is not None:
                try:
                    self.view.removeItem(item)
                except Exception:
                    pass
        self._waypoint_item = None
        self._selection_item = None
        self._grid = None
        self._axis = None
        self._basemap_item = None

    @staticmethod
    def _rgba(color: QColor, alpha: float = 1.0):
        return np.array([color.redF(), color.greenF(), color.blueF(), alpha], dtype=float)

    def _vertical_scale(self) -> float:
        return self.VERTICAL_SCALES.get(self.vertical_combo.currentText(), 5.0)

    def _render_scene(self):
        if self.session is None or self.route is None:
            return
        self._clear_scene()
        scale = self._vertical_scale()
        r = self.route

        valid_idx = np.where(r.valid)[0]
        if not len(valid_idx):
            self.legend.hide()
            return

        # Optional georeferenced raster map plane beneath the route.
        if self._basemap_raster is not None:
            raster = self._basemap_raster
            rgba = raster.rgba.copy()
            opacity = self.basemap_opacity.value() / 100.0
            rgba[..., 3] = np.clip(rgba[..., 3].astype(float) * opacity, 0, 255).astype(np.uint8)
            # GLImageItem uses its first two array dimensions as X/Y, so convert
            # north-at-top row-major pixels into local east/north coordinates.
            texture = np.transpose(np.flipud(rgba), (1, 0, 2)).copy()
            try:
                self._basemap_item = gl.GLImageItem(texture)
                self._basemap_item.setGLOptions('translucent')
                sx = raster.width_m / max(texture.shape[0], 1)
                sy = raster.height_m / max(texture.shape[1], 1)
                self._basemap_item.scale(sx, sy, 1.0)
                self._basemap_item.translate(raster.x_min_m, raster.y_min_m, -0.35)
                self.view.addItem(self._basemap_item)
            except Exception as exc:
                self._basemap_item = None
                self.map_attribution.setText(f'3D basemap rendering failed: {exc}')

        # Ground grid centered under the route.
        xvals = r.x_m[r.valid]
        yvals = r.y_m[r.valid]
        dx = max(float(np.ptp(xvals)), 40.0)
        dy = max(float(np.ptp(yvals)), 40.0)
        cx = float((np.nanmin(xvals) + np.nanmax(xvals)) / 2.0)
        cy = float((np.nanmin(yvals) + np.nanmax(yvals)) / 2.0)
        spacing = max(10.0, round(max(dx, dy) / 8.0 / 5.0) * 5.0)
        self._grid = gl.GLGridItem()
        self._grid.setSize(x=dx * 1.25, y=dy * 1.25)
        self._grid.setSpacing(x=spacing, y=spacing)
        self._grid.translate(cx, cy, 0.0)
        self.view.addItem(self._grid)

        self._axis = gl.GLAxisItem()
        self._axis.setSize(x=min(dx, 35.0), y=min(dy, 35.0), z=max(15.0, float(np.nanmax(r.relative_altitude_m[r.valid])) * scale))
        self.view.addItem(self._axis)

        definition = OVERLAYS_BY_LABEL[self.overlay_combo.currentText()]
        values = None
        value_range = None
        if definition.column is not None:
            values = overlay_values(self.session.samples, definition)
            value_range = robust_value_range(values[r.valid])
            if value_range:
                self.legend.set_range(definition.label, value_range[0], value_range[1], definition.unit, definition.reverse_scale)
            else:
                self.legend.hide()
        else:
            self.legend.hide()

        for run in contiguous_valid_runs(r.valid):
            if len(run) < 2:
                continue
            pos = np.column_stack((
                r.x_m[run],
                r.y_m[run],
                r.relative_altitude_m[run] * scale,
            )).astype(float)

            if values is not None and value_range is not None:
                lo, hi = value_range
                colors = []
                for value in values[run]:
                    if np.isfinite(value):
                        c = _value_color(value, lo, hi, definition.reverse_scale)
                    else:
                        c = QColor('#687888')
                    colors.append(self._rgba(c))
                colors = np.asarray(colors, dtype=float)
            else:
                colors = np.tile(np.array([[0.345, 0.651, 1.0, 1.0]], dtype=float), (len(run), 1))

            item = gl.GLLinePlotItem(pos=pos, color=colors, width=3.0, antialias=True, mode='line_strip')
            self.view.addItem(item)
            self._route_items.append(item)

        first, last = valid_idx[0], valid_idx[-1]
        endpoints = np.array([
            [r.x_m[first], r.y_m[first], r.relative_altitude_m[first] * scale],
            [r.x_m[last], r.y_m[last], r.relative_altitude_m[last] * scale],
        ], dtype=float)
        endpoint_colors = np.array([
            [0.247, 0.725, 0.314, 1.0],
            [0.973, 0.318, 0.286, 1.0],
        ], dtype=float)
        endpoint_item = gl.GLScatterPlotItem(pos=endpoints, color=endpoint_colors, size=13.0, pxMode=True)
        self.view.addItem(endpoint_item)
        self._route_items.append(endpoint_item)

        # Waypoints use source sample IDs so their 3D position exactly follows the recorded route.
        wp_positions = []
        if not self.session.waypoints.empty:
            id_to_index = {int(sid): i for i, sid in enumerate(r.sample_ids)}
            for _, row in self.session.waypoints.iterrows():
                try:
                    i = id_to_index.get(int(row.get('source_sample_id')))
                except Exception:
                    i = None
                if i is not None and r.valid[i]:
                    wp_positions.append([r.x_m[i], r.y_m[i], r.relative_altitude_m[i] * scale])
        if wp_positions:
            self._waypoint_item = gl.GLScatterPlotItem(
                pos=np.asarray(wp_positions, dtype=float),
                color=np.tile(np.array([[0.824, 0.600, 0.133, 1.0]]), (len(wp_positions), 1)),
                size=11.0, pxMode=True)
            self.view.addItem(self._waypoint_item)

        self._selection_item = gl.GLScatterPlotItem(
            pos=np.empty((0, 3), dtype=float),
            color=np.array([[1.0, 1.0, 1.0, 1.0]], dtype=float),
            size=16.0, pxMode=True)
        self.view.addItem(self._selection_item)

        if self.controller.sample_id is not None:
            self._selection_changed(self.controller.sample_id)

    def _route_center_extent(self):
        if self.route is None or not self.route.valid.any():
            return (0.0, 0.0, 0.0, 100.0)
        r = self.route
        scale = self._vertical_scale()
        x = r.x_m[r.valid]
        y = r.y_m[r.valid]
        z = r.relative_altitude_m[r.valid] * scale
        cx = float((np.nanmin(x) + np.nanmax(x)) / 2.0)
        cy = float((np.nanmin(y) + np.nanmax(y)) / 2.0)
        cz = float((np.nanmin(z) + np.nanmax(z)) / 2.0)
        extent = max(float(np.ptp(x)), float(np.ptp(y)), float(np.ptp(z)), 40.0)
        return cx, cy, cz, extent

    def fit_view(self):
        cx, cy, cz, extent = self._route_center_extent()
        self.view.opts['center'] = QVector3D(cx, cy, cz)
        self.view.setCameraPosition(distance=extent * 1.55, elevation=28, azimuth=-48)
        self.view.update()

    def top_view(self):
        cx, cy, cz, extent = self._route_center_extent()
        self.view.opts['center'] = QVector3D(cx, cy, cz)
        self.view.setCameraPosition(distance=extent * 1.55, elevation=89.9, azimuth=0)
        self.view.update()

    def perspective_view(self):
        self.fit_view()

    def _slider_changed(self, index: int):
        if self.session is None or index < 0 or index >= len(self.session.samples):
            return
        sample_id = int(self.session.samples.iloc[index]['sample_id'])
        self.controller.select(sample_id)

    def _selection_changed(self, sample_id: int):
        if self.session is None or self.route is None:
            return
        matches = np.where(self.route.sample_ids == int(sample_id))[0]
        if not len(matches):
            return
        i = int(matches[0])
        self.sample_slider.blockSignals(True)
        self.sample_slider.setValue(i)
        self.sample_slider.blockSignals(False)
        self.slider_label.setText(f'Sample {sample_id} · {i + 1}/{len(self.route.sample_ids)}')
        self.inspector.set_sample(self.session, sample_id)

        if self._selection_item is not None:
            if self.route.valid[i]:
                scale = self._vertical_scale()
                pos = np.array([[self.route.x_m[i], self.route.y_m[i], self.route.relative_altitude_m[i] * scale]], dtype=float)
                self._selection_item.setData(pos=pos, color=np.array([[1.0, 1.0, 1.0, 1.0]]), size=16.0, pxMode=True)
            else:
                self._selection_item.setData(pos=np.empty((0, 3), dtype=float))

