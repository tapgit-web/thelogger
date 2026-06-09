"""
dashboard.py  —  Live Monitoring Dashboard
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSplitter, QTextEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QColor
import pyqtgraph as pg

from .icons import btn_icon, icon


DEFAULT_NAMES = ["Voltage R","Voltage Y","Voltage B","Current R","Current Y",
                 "Current B","Power Factor","Frequency","Active Power","Reactive Power", "Temperature"]
DEFAULT_UNITS = ["V","V","V","A","A","A","PF","Hz","kW","kVAR", "°C"]
COLS = 4

# Card accent colours cycling per register index
CARD_ACCENTS = [
    "#10B981", "#1976D2", "#1B873F", "#E17000",
    "#6F42C1", "#E83E8C", "#20C997", "#0097A7",
    "#795548", "#546E7A",
]


class ValueCard(QFrame):
    """Single register value card — premium design."""

    def __init__(self, name: str, unit: str, val_id: str, accent: str = "#10B981", parent=None):
        super().__init__(parent)
        self.val_id  = val_id
        self._accent = accent
        self.setObjectName("valueCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedSize(QSize(220, 140))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Click to view live trend for {name}")

        # Card shell styling — white bg, subtle border, rounded, hover
        self.setStyleSheet(f"""
            QFrame#valueCard {{
                background-color: #FFFFFF;
                border: 1.5px solid #E8EAED;
                border-top: 4px solid {accent};
                border-radius: 10px;
            }}
            QFrame#valueCard:hover {{
                border: 1.5px solid {accent};
                border-top: 4px solid {accent};
                background-color: #FAFBFF;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # ── Register name ────────────────────────────────────────────
        self.name_lbl = QLabel(name.upper())
        self.name_lbl.setStyleSheet(
            f"color:#5E6C84; font-size:7.5pt; font-weight:700; "
            f"letter-spacing:0.6px; background:transparent;"
        )
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.name_lbl.setWordWrap(True)

        # ── Divider ─────────────────────────────────────────────────
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{accent}22; border:none;")

        # ── Value + unit row ─────────────────────────────────────────
        val_row = QHBoxLayout()
        val_row.setSpacing(6)
        val_row.setContentsMargins(0, 0, 0, 0)

        self.val_lbl = QLabel("---")
        self.val_lbl.setStyleSheet(
            f"color:{accent}; font-size:22pt; font-weight:700; "
            f"background:transparent; letter-spacing:-0.5px;"
        )
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Unit pill badge
        self.unit_lbl = QLabel(unit if unit else "—")
        self.unit_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.unit_lbl.setStyleSheet(
            f"color:#FFFFFF; background:{accent}; font-size:7pt; font-weight:700; "
            f"border-radius:3px; padding:2px 6px; margin-bottom:4px;"
        )

        val_row.addWidget(self.val_lbl)
        val_row.addWidget(self.unit_lbl, alignment=Qt.AlignmentFlag.AlignBottom)
        val_row.addStretch()

        layout.addWidget(self.name_lbl)
        layout.addWidget(div)
        layout.addLayout(val_row)
        layout.addStretch()

    def update_value(self, val_str: str):
        self.val_lbl.setText(val_str)


class DeviceBlock(QFrame):
    """One device section with header + value cards."""

    def __init__(self, device: dict, live_values: dict, on_card_click, is_running=False, parent=None):
        super().__init__(parent)
        self.device = device
        self.cards: dict[str, ValueCard] = {}
        self.setStyleSheet("background:transparent; border:none;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 8, 20, 0)
        outer.setSpacing(8)

        # ── Header ───────────────────────────────────────────────────
        head = QFrame()
        head.setObjectName("deviceHead")
        head_lay = QHBoxLayout(head)
        head_lay.setContentsMargins(16, 10, 16, 10)
        head_lay.setSpacing(10)

        # Status dot
        status_lbl = QLabel()
        status_lbl.setFixedSize(10, 10)
        color = "#1B873F" if is_running else "#B3BAC5"
        status_lbl.setStyleSheet(f"background:{color}; border-radius:5px;")

        ip    = device['ip']
        slave = device.get('slave_id', 1)
        dname = device.get('device_name', '')
        title_txt = dname.upper() if dname else f"NODE  {ip} / SLAVE {slave}"

        title = QLabel(title_txt)
        title.setObjectName("section_heading")

        self.sync_lbl = QLabel("Last sync: —")
        self.sync_lbl.setObjectName("dim")
        self.sync_lbl.setStyleSheet(
            "color:#8993A4; font-size:7.5pt; font-family:Consolas; background:transparent;"
        )

        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        info_col.addWidget(title)
        info_col.addWidget(self.sync_lbl)

        head_lay.addWidget(status_lbl)
        head_lay.addLayout(info_col)
        head_lay.addStretch()

        ICON_SIZE = QSize(13, 13)
        BTN_STYLES = {
            "success_btn": "background-color:#1B873F; color:#FFFFFF; font-size:9pt; font-weight:600; border:none; border-radius:4px; padding:0 10px;",
            "danger_btn":  "background-color:#D32F2F; color:#FFFFFF; font-size:9pt; font-weight:600; border:none; border-radius:4px; padding:0 10px;",
            "neutral_btn": "background-color:#FFFFFF;  color:#42526E; font-size:9pt; font-weight:600; border:1px solid #DFE1E6; border-radius:4px; padding:0 10px;",
        }
        for label, alias, obj, slot in [
            ("  Start",   "start",   "success_btn", lambda: on_card_click('start',   device)),
            ("  Stop",    "stop",    "danger_btn",  lambda: on_card_click('stop',    device)),
            ("  Refresh", "refresh", "neutral_btn", lambda: on_card_click('refresh', device)),
        ]:
            b = QPushButton(label)
            b.setObjectName(obj)
            b.setFixedHeight(30)
            b.setIconSize(ICON_SIZE)
            b.setIcon(btn_icon(alias))
            b.setStyleSheet(f"QPushButton {{ {BTN_STYLES[obj]} }}")
            b.clicked.connect(slot)
            head_lay.addWidget(b)

        outer.addWidget(head)

        # ── Cards grid ───────────────────────────────────────────────
        cards_widget = QWidget()
        cards_widget.setStyleSheet("background:transparent;")
        cards_grid = QGridLayout(cards_widget)
        cards_grid.setSpacing(12)
        cards_grid.setContentsMargins(0, 4, 0, 8)

        ct   = device.get('conn_type', 'TCP')
        port = device['port']

        for i, reg in enumerate(device['registers']):
            r_str  = str(reg)
            name   = device.get('names', {}).get(r_str) or \
                     (DEFAULT_NAMES[i] if i < len(DEFAULT_NAMES) else f"REG {reg}")
            unit   = device.get('units', {}).get(r_str) or \
                     (DEFAULT_UNITS[i] if i < len(DEFAULT_UNITS) and i < len(DEFAULT_NAMES) else "")
            val_id = (f"{ip}:{port}:{slave}:{reg}" if ct == "TCP"
                      else f"{ip}:{slave}:{reg}")
            accent = CARD_ACCENTS[i % len(CARD_ACCENTS)]

            card = ValueCard(name, unit, val_id, accent=accent)
            if val_id in live_values:
                card.update_value(live_values[val_id])

            card.mousePressEvent = (
                lambda e, lid=val_id, nm=name: on_card_click('graph', device, lid, nm)
            )
            cards_grid.addWidget(card, i // COLS, i % COLS)
            self.cards[val_id] = card

        outer.addWidget(cards_widget)

    def update_card(self, val_id: str, value: str):
        if val_id in self.cards:
            self.cards[val_id].update_value(value)

    def update_sync_time(self):
        from datetime import datetime
        self.sync_lbl.setText(f"Last sync: {datetime.now().strftime('%H:%M:%S')}")


class LiveTrendChart(QWidget):
    """Compact PyQtGraph line chart for a single register."""
    MAX_POINTS = 120

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.title_lbl = QLabel("Select a card to view live trend")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet(
            "color:#8993A4; font-size:8pt; font-style:italic; background:transparent;"
        )

        pg.setConfigOptions(antialias=True)
        self.pw = pg.PlotWidget(background="#FFFFFF")
        self.pw.showGrid(x=False, y=True, alpha=0.15)
        ax_pen = pg.mkPen(color='#DFE1E6', width=1)
        self.pw.getAxis('left').setPen(ax_pen)
        self.pw.getAxis('bottom').setPen(ax_pen)
        self.pw.getAxis('left').setTextPen(pg.mkPen('#5E6C84'))
        self.pw.getAxis('bottom').setTextPen(pg.mkPen('#5E6C84'))
        self.pw.setStyleSheet("border: 1px solid #DFE1E6; border-radius: 6px;")
        self.pw.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        fill = pg.mkBrush(color=(211, 47, 47, 30))
        self.curve = self.pw.plot(
            pen=pg.mkPen(color='#10B981', width=2.5),
            fillLevel=0, brush=fill
        )
        self._data: list[float] = []

        layout.addWidget(self.title_lbl)
        layout.addWidget(self.pw, stretch=1)

    def update_series(self, val_id: str, name: str, value: float):
        self.title_lbl.setText(name.upper())
        self._data.append(value)
        if len(self._data) > self.MAX_POINTS:
            self._data = self._data[-self.MAX_POINTS:]
        self.curve.setData(self._data)

    def reset(self):
        self._data.clear()
        self.curve.setData([])
        self.title_lbl.setText("Select a card to view live trend")


class DashboardView(QWidget):
    """Main dashboard: device blocks (left) + trend chart + log (right)."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._device_blocks: list[DeviceBlock] = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Control bar ──────────────────────────────────────────────
        ctrl = QFrame()
        ctrl.setObjectName("ctrl_bar")
        ctrl.setStyleSheet("QFrame#ctrl_bar { background-color:#FFFFFF; border-bottom:1px solid #DFE1E6; }")
        ctrl.setFixedHeight(52)
        ctrl_lay = QHBoxLayout(ctrl)
        ctrl_lay.setContentsMargins(20, 0, 20, 0)
        ctrl_lay.setSpacing(10)

        self.status_lbl = QLabel("0 / 0 Nodes Online")
        self.status_lbl.setStyleSheet(
            "color:#5E6C84; font-size:9pt; font-weight:600; background:transparent;"
        )

        btn_start = QPushButton("  Start All Nodes")
        btn_start.setObjectName("success_btn")
        btn_start.setIcon(btn_icon("start_all"))
        btn_start.setIconSize(QSize(14, 14))
        btn_start.setFixedHeight(32)
        btn_start.setStyleSheet("""
            QPushButton { background-color:#1B873F; color:#FFFFFF; font-size:9pt;
                          font-weight:600; border:none; border-radius:4px; padding:0 14px; }
            QPushButton:hover { background-color:#146B32; }
            QPushButton:pressed { background-color:#0E5227; }
        """)
        btn_start.clicked.connect(self.app.start_all_devices)

        btn_stop = QPushButton("  Stop All Nodes")
        btn_stop.setObjectName("danger_btn")
        btn_stop.setIcon(btn_icon("stop_all"))
        btn_stop.setIconSize(QSize(14, 14))
        btn_stop.setFixedHeight(32)
        btn_stop.setStyleSheet("""
            QPushButton { background-color:#D32F2F; color:#FFFFFF; font-size:9pt;
                          font-weight:600; border:none; border-radius:4px; padding:0 14px; }
            QPushButton:hover { background-color:#C62828; }
            QPushButton:pressed { background-color:#B71C1C; }
        """)
        btn_stop.clicked.connect(self.app.stop_all_devices)

        ctrl_lay.addWidget(self.status_lbl)
        ctrl_lay.addStretch()
        ctrl_lay.addWidget(btn_start)
        ctrl_lay.addWidget(btn_stop)
        root.addWidget(ctrl)

        # ── Splitter ─────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── LEFT: scrollable device cards ────────────────────────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setStyleSheet("QScrollArea { border:none; background:#F4F5F7; } QScrollArea > QWidget { background:#F4F5F7; }")
        left_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.devices_container = QWidget()
        self.devices_container.setStyleSheet("background-color:#F4F5F7;")
        self.devices_layout = QVBoxLayout(self.devices_container)
        self.devices_layout.setContentsMargins(0, 12, 0, 12)
        self.devices_layout.setSpacing(0)

        self.empty_lbl = QLabel(
            "No devices configured.\n\nGo to Device Manager to add your first node."
        )
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet(
            "color:#C1C7D0; font-size:13pt; background:transparent;"
        )
        self.empty_lbl.setVisible(False)
        self.devices_layout.addWidget(self.empty_lbl)
        self.devices_layout.addStretch()
        left_scroll.setWidget(self.devices_container)

        # ── RIGHT: analytics panel — expands to fill splitter pane ───
        right_sidebar = QFrame()
        right_sidebar.setObjectName("panel_frame")
        right_sidebar.setMinimumWidth(280)
        right_sidebar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_sidebar.setStyleSheet("QFrame#panel_frame { background-color:#FFFFFF; border-left:1px solid #DFE1E6; }")

        right_lay = QVBoxLayout(right_sidebar)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        # ── Live Trend section (60% of right height) ──────────────────
        chart_sec = QFrame()
        chart_sec.setObjectName("chart_sec")
        chart_sec.setStyleSheet("QFrame#chart_sec { background-color:#FFFFFF; border-bottom:1px solid #DFE1E6; }")
        chart_sec.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        chart_lay = QVBoxLayout(chart_sec)
        chart_lay.setContentsMargins(14, 12, 14, 12)
        chart_lay.setSpacing(6)

        chart_hdr = QHBoxLayout()
        chart_icon_lbl = QLabel()
        chart_icon_lbl.setPixmap(icon("fa5s.chart-line", "#10B981").pixmap(QSize(14, 14)))
        chart_icon_lbl.setStyleSheet("background:transparent;")
        chart_title = QLabel("Live Trend")
        chart_title.setStyleSheet(
            "color:#10B981; font-size:8.5pt; font-weight:700; "
            "letter-spacing:0.5px; background:transparent;"
        )
        chart_hdr.addWidget(chart_icon_lbl)
        chart_hdr.addSpacing(4)
        chart_hdr.addWidget(chart_title)
        chart_hdr.addStretch()

        self.trend_chart = LiveTrendChart()
        chart_lay.addLayout(chart_hdr)
        chart_lay.addWidget(self.trend_chart, stretch=1)

        right_lay.addWidget(chart_sec, stretch=3)   # 60% of right panel

        # ── Activity Log section (40% of right height) ────────────────
        log_sec = QFrame()
        log_sec.setObjectName("log_sec")
        log_sec.setStyleSheet("QFrame#log_sec { background-color:#FFFFFF; }")
        log_sec.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        log_lay = QVBoxLayout(log_sec)
        log_lay.setContentsMargins(14, 10, 14, 10)
        log_lay.setSpacing(6)

        log_hdr = QHBoxLayout()
        log_icon_lbl = QLabel()
        log_icon_lbl.setPixmap(icon("fa5s.terminal", "#5E6C84").pixmap(QSize(13, 13)))
        log_icon_lbl.setStyleSheet("background:transparent;")
        log_title = QLabel("Activity Log")
        log_title.setStyleSheet(
            "color:#5E6C84; font-size:8.5pt; font-weight:700; "
            "letter-spacing:0.5px; background:transparent;"
        )
        log_hdr.addWidget(log_icon_lbl)
        log_hdr.addSpacing(4)
        log_hdr.addWidget(log_title)
        log_hdr.addStretch()

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log_box.setStyleSheet("""
            QTextEdit {
                background:#F4F5F7;
                font-family:Consolas, monospace;
                font-size:8.5pt;
                color:#172B4D;
                border:1px solid #DFE1E6;
                border-radius:4px;
            }
        """)
        log_lay.addLayout(log_hdr)
        log_lay.addWidget(self.log_box, stretch=1)

        right_lay.addWidget(log_sec, stretch=2)   # 40% of right panel

        # ── Wire up splitter ──────────────────────────────────────────
        splitter.addWidget(left_scroll)
        splitter.addWidget(right_sidebar)
        # Default split: left 70%, right 30% — user can drag to resize
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, stretch=1)

    # ── Public API ────────────────────────────────────────────────────
    def rebuild_device_blocks(self, devices, running_keys, live_values):
        """Re-populate the device card grid. Safe to call multiple times."""
        self._device_blocks.clear()

        # Remove all widgets EXCEPT the persistent empty_lbl
        for i in reversed(range(self.devices_layout.count())):
            item = self.devices_layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w is self.empty_lbl:
                continue
            if item.spacerItem():
                self.devices_layout.removeItem(item)
                continue
            if w:
                self.devices_layout.removeWidget(w)
                w.setParent(None)

        if not devices:
            self.empty_lbl.setVisible(True)
            self.devices_layout.addStretch()
            return

        self.empty_lbl.setVisible(False)
        for dev in devices:
            ip, port = dev['ip'], dev['port']
            slave    = dev.get('slave_id', 1)
            ct       = dev.get('conn_type', 'TCP')
            key      = f"{ip}:{port}:{slave}" if ct == "TCP" else f"{ip}:{slave}"
            block = DeviceBlock(
                device=dev, live_values=live_values,
                on_card_click=self._on_card_action,
                is_running=(key in running_keys),
                parent=self.devices_container
            )
            self._device_blocks.append(block)
            self.devices_layout.addWidget(block)

        self.devices_layout.addStretch()
        self._update_status(devices, running_keys)

    def _update_status(self, devices, running_keys):
        active = 0
        for dev in devices:
            ip, port = dev['ip'], dev['port']
            slave = dev.get('slave_id', 1)
            ct    = dev.get('conn_type', 'TCP')
            key   = f"{ip}:{port}:{slave}" if ct == "TCP" else f"{ip}:{slave}"
            if key in running_keys:
                active += 1
        total = len(devices)
        c = "#1B873F" if active > 0 else "#5E6C84"
        self.status_lbl.setStyleSheet(
            f"color:{c}; font-size:9pt; font-weight:600; background:transparent;"
        )
        self.status_lbl.setText(f"{active} / {total} Nodes Online")

    def _on_card_action(self, action, device, val_id=None, name=None):
        if action == 'start':
            self.app.start_device(device)
        elif action == 'stop':
            self.app.stop_device(device)
        elif action == 'refresh':
            self.app.refresh_device(device)
        elif action == 'graph' and val_id:
            self.app.set_selected_graph(val_id, name)

    @pyqtSlot(str, str)
    def on_data_received(self, val_id: str, value: str):
        for block in self._device_blocks:
            block.update_card(val_id, value)
            block.update_sync_time()
        if val_id == self.app.selected_graph_lid:
            try:
                self.trend_chart.update_series(
                    val_id, self.app.selected_graph_name, float(value)
                )
            except:
                pass

    @pyqtSlot(str)
    def append_log(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(
            f"<span style='color:#8993A4;'>[{ts}]</span> "
            f"<span style='color:#172B4D;'>{msg}</span>"
        )
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_graph_target(self, val_id: str, name: str):
        self.trend_chart.reset()
        self.trend_chart.title_lbl.setText(name.upper())
