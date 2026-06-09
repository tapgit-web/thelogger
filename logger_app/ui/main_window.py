"""
main_window.py  —  PyQt6 Main Application Window
Handles: Sidebar navigation, thread management, signal routing.
"""

import os, csv, hashlib, threading, shutil, webbrowser
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QMessageBox, QSizePolicy,
    QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QIcon

from ..backend.core import (
    load_devices, save_devices, load_email_settings, save_email_settings,
    load_users, save_users, load_trend_settings, save_trend_settings,
    write_alarm_history_csv, write_email_log_csv, DATA_PATH, resource_path
)
from ..backend.modbus_worker import ModbusWorker
from .icons import btn_icon, nav_icon, icon

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import letter, landscape
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# ── Nav items: (view_id, display_label, icon_alias) ──────────────────
NAV_ITEMS = [
    ("live_data",    "Dashboard",      "dashboard"),
    ("add_device",   "Device Manager", "device_mgr"),
    ("live_log",     "Live Log",       "live_log"),
    ("email_config", "Alarm Config",   "alarm_cfg"),
    ("export_data",  "Data Export",    "export"),
    ("data_trends",  "Historic Trends","trends"),
    ("user_manager", "System Users",   "users"),
]

VIEW_TITLES = {
    "live_data":       "MONITORING DASHBOARD",
    "add_device":      "DEVICE CONFIGURATION",
    "live_log":        "SYSTEM ANALYTICS",
    "email_config":    "ALARM CONFIGURATION",
    "export_data":     "DATA EXPORT",
    "data_trends":     "HISTORIC TREND ANALYTICS",
    "user_manager":    "USER MANAGEMENT",
    "email_alerts":    "ALARM HISTORY",
    "email_logs_view": "EMAIL SEND LOGS",
}


class MainWindow(QMainWindow):
    def __init__(self, current_user: str):
        super().__init__()
        self.current_user = current_user

        # ── State ────────────────────────────────────────────────────
        self.devices        = load_devices()
        self.email_settings = load_email_settings()
        self.users          = load_users()
        self.trend_settings = load_trend_settings()
        self.global_log     = []
        self.live_values    = {}
        self.data_history   = {}
        self.workers: dict[str, ModbusWorker] = {}
        self.alert_cooldowns = {}
        self.alert_lock     = threading.Lock()
        self.selected_graph_lid  = None
        self.selected_graph_name = ""
        self.active_view    = "live_data"

        self._build_window()
        self._build_sidebar()
        self._build_content_area()
        self.navigate("live_data")

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._periodic_refresh)
        self._refresh_timer.start(5000)

    # ═════════════════════════════════════════════════════════════════
    # WINDOW SHELL
    # ═════════════════════════════════════════════════════════════════
    def _build_window(self):
        self.setWindowTitle("THE LOGGER — Industrial Monitoring")
        self.setMinimumSize(1280, 780)
        self.showMaximized()

        icon_p = resource_path("icon.png")
        if os.path.exists(icon_p):
            self.setWindowIcon(QIcon(icon_p))

        qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())

        central = QWidget()
        self.setCentralWidget(central)
        self._root_layout = QHBoxLayout(central)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

    # ═════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ═════════════════════════════════════════════════════════════════
    def _build_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(230)

        sb = QVBoxLayout(self.sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        # ── Logo strip ───────────────────────────────────────────────
        logo_frame = QFrame()
        logo_frame.setObjectName("logo_frame")
        logo_frame.setFixedHeight(64)
        lf_lay = QHBoxLayout(logo_frame)
        lf_lay.setContentsMargins(22, 0, 22, 0)

        chart_icon_lbl = QLabel()
        chart_icon_lbl.setPixmap(
            icon("fa5s.chart-line", "#10B981", 22).pixmap(QSize(28, 28))
        )
        chart_icon_lbl.setStyleSheet("background: transparent;")

        logo_lbl = QLabel("<span style='color:#10B981; font-weight:700;'>THE</span> <span style='color:#172B4D; font-weight:300;'>LOGGER</span>")
        logo_lbl.setStyleSheet(
            "font-size:18pt; background:transparent;"
        )

        lf_lay.addWidget(chart_icon_lbl)
        lf_lay.addSpacing(8)
        lf_lay.addWidget(logo_lbl)
        lf_lay.addStretch()
        sb.addWidget(logo_frame)

        # ── Nav items ────────────────────────────────────────────────
        self._nav_btns: dict[str, QPushButton] = {}
        user_perms = self.users.get(self.current_user, {}).get("permissions", [])

        for view_id, label, icon_alias in NAV_ITEMS:
            if view_id not in user_perms:
                continue
            btn = QPushButton(f"  {label}")
            btn.setObjectName("nav_btn")
            btn.setCheckable(False)
            btn.setFixedHeight(46)
            btn.setIconSize(QSize(16, 16))
            btn.setIcon(nav_icon(icon_alias, active=False))
            btn.clicked.connect(lambda _, vid=view_id, ia=icon_alias: self.navigate(vid))
            sb.addWidget(btn)
            self._nav_btns[view_id] = btn

        sb.addStretch()

        # ── Footer ───────────────────────────────────────────────────
        footer = QFrame()
        footer.setObjectName("sidebar_footer")
        footer.setFixedHeight(52)
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(18, 0, 14, 0)
        foot_lay.setSpacing(8)

        user_icon_lbl = QLabel()
        user_icon_lbl.setPixmap(
            icon("fa5s.user-circle", "#5E6C84", 14).pixmap(QSize(18, 18))
        )
        user_icon_lbl.setStyleSheet("background: transparent;")

        user_lbl = QLabel(self.current_user.upper())
        user_lbl.setStyleSheet(
            "color:#5E6C84; font-size:8pt; font-weight:600; background:transparent;"
        )

        logout_btn = QPushButton("  Sign Out")
        logout_btn.setObjectName("danger_btn")
        logout_btn.setFixedHeight(28)
        logout_btn.setIconSize(QSize(13, 13))
        logout_btn.setIcon(btn_icon("logout"))
        logout_btn.clicked.connect(self._logout)

        foot_lay.addWidget(user_icon_lbl)
        foot_lay.addWidget(user_lbl)
        foot_lay.addStretch()
        foot_lay.addWidget(logout_btn)
        sb.addWidget(footer)

        self._root_layout.addWidget(self.sidebar)

    # ═════════════════════════════════════════════════════════════════
    # CONTENT AREA
    # ═════════════════════════════════════════════════════════════════
    def _build_content_area(self):
        right = QWidget()
        right.setStyleSheet(".QFrame { background-color:#F4F5F7; }")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(56)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(28, 0, 28, 0)

        self.view_title = QLabel("MONITORING DASHBOARD")
        self.view_title.setObjectName("page_title")
        top_layout.addWidget(self.view_title)
        top_layout.addStretch()

        # HWID badge
        from ..backend.core import get_hwid
        hwid_lbl = QLabel(f"HWID: {get_hwid()}")
        hwid_lbl.setStyleSheet(
            "color:#8993A4; font-size:7.5pt; font-family:Consolas; background:transparent;"
        )
        top_layout.addWidget(hwid_lbl)

        right_layout.addWidget(top_bar)

        # ── Stacked pages ────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(".QStackedWidget { background-color:#F4F5F7; }")
        right_layout.addWidget(self.stack, stretch=1)

        self._root_layout.addWidget(right, stretch=1)
        self._views: dict[str, QWidget] = {}

    # ═════════════════════════════════════════════════════════════════
    # NAVIGATION
    # ═════════════════════════════════════════════════════════════════
    def navigate(self, view_id: str):
        self.active_view = view_id
        self.view_title.setText(VIEW_TITLES.get(view_id, ""))

        for vid, btn in self._nav_btns.items():
            active = (vid == view_id)
            btn.setProperty("active", "true" if active else "false")
            # Update icon color
            for _, label, alias in NAV_ITEMS:
                if vid == [i[0] for i in NAV_ITEMS if i[0]==vid][0]:
                    break
            for item_id, _, alias in NAV_ITEMS:
                if item_id == vid:
                    btn.setIcon(nav_icon(alias, active=active))
                    break
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if view_id not in self._views:
            self._views[view_id] = self._create_view(view_id)
            self.stack.addWidget(self._views[view_id])

        self.stack.setCurrentWidget(self._views[view_id])

        if view_id == "live_data":
            running = {k for k, w in self.workers.items() if w.isRunning()}
            self._views["live_data"].rebuild_device_blocks(
                self.devices, running, self.live_values
            )

    def _create_view(self, view_id: str) -> QWidget:
        from .dashboard       import DashboardView
        from .device_manager  import DeviceManagerView
        from .other_views     import (LiveLogView, AlarmConfigView,
                                      DataExportView, UserManagerView)
        from .trends_view     import TrendsView

        if view_id == "live_data":
            return DashboardView(self)
        elif view_id == "add_device":
            running = {k for k, w in self.workers.items() if w.isRunning()}
            v = DeviceManagerView(self.devices, running)
            v.devices_changed.connect(self._on_devices_changed)
            return v
        elif view_id == "live_log":
            return LiveLogView(self)
        elif view_id == "email_config":
            v = AlarmConfigView(self.email_settings, self.devices,
                                self.current_user, self.users)
            v.settings_saved.connect(self._on_email_settings_saved)
            return v
        elif view_id == "export_data":
            return DataExportView(self)
        elif view_id == "data_trends":
            return TrendsView(self)
        elif view_id == "user_manager":
            v = UserManagerView(self.users)
            v.users_changed.connect(self._on_users_changed)
            return v
        elif view_id == "email_alerts":
            return self._build_alarm_history_view()
        elif view_id == "email_logs_view":
            return self._build_email_logs_view()
        return QWidget()

    # ── Quick sub-views ───────────────────────────────────────────────
    def _build_alarm_history_view(self) -> QWidget:
        from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView
        w = QWidget(); layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 12, 24, 12)

        bar = QHBoxLayout()
        back = QPushButton("  Back to Log")
        back.setObjectName("dark_btn")
        back.setIconSize(QSize(14, 14))
        back.setIcon(btn_icon("back"))
        back.clicked.connect(lambda: self.navigate("live_log"))

        exp = QPushButton("  Export CSV")
        exp.setObjectName("blue_btn")
        exp.setIcon(btn_icon("download"))
        exp.setIconSize(QSize(14, 14))
        exp.clicked.connect(self._export_alarm_csv)

        bar.addWidget(back); bar.addStretch(); bar.addWidget(exp)
        layout.addLayout(bar)

        tree = QTreeWidget()
        tree.setColumnCount(7)
        tree.setHeaderLabels(["TIMESTAMP","DEVICE","FIELD","ADDR","READING","CONDITION","THRESHOLD"])
        tree.setRootIsDecorated(False); tree.setAlternatingRowColors(True)
        tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(tree)

        date_str = datetime.now().strftime("%Y-%m-%d")
        fn = os.path.join(DATA_PATH, "live", f"Alarm_History_{date_str}.csv")
        if os.path.exists(fn):
            with open(fn) as f:
                reader = csv.reader(f); next(reader, None)
                for row in reader:
                    if row: tree.addTopLevelItem(QTreeWidgetItem(row))
        return w

    def _build_email_logs_view(self) -> QWidget:
        from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView
        w = QWidget(); layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 12, 24, 12)

        bar = QHBoxLayout()
        back = QPushButton("  Back to Log")
        back.setObjectName("dark_btn")
        back.setIcon(btn_icon("back"))
        back.setIconSize(QSize(14, 14))
        back.clicked.connect(lambda: self.navigate("live_log"))
        bar.addWidget(back); bar.addStretch()
        layout.addLayout(bar)

        tree = QTreeWidget()
        tree.setColumnCount(5)
        tree.setHeaderLabels(["TIMESTAMP","DEVICE","FIELD","RECIPIENT","STATUS"])
        tree.setRootIsDecorated(False); tree.setAlternatingRowColors(True)
        tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(tree)

        date_str = datetime.now().strftime("%Y-%m-%d")
        fn = os.path.join(DATA_PATH, "live", f"Email_Logs_{date_str}.csv")
        if os.path.exists(fn):
            with open(fn) as f:
                reader = csv.reader(f); next(reader, None)
                for row in reader:
                    if row: tree.addTopLevelItem(QTreeWidgetItem(row))
        return w

    # ═════════════════════════════════════════════════════════════════
    # DEVICE CONTROL
    # ═════════════════════════════════════════════════════════════════
    def start_device(self, dev: dict):
        ip, port, slave = dev['ip'], dev['port'], dev.get('slave_id', 1)
        ct  = dev.get('conn_type', 'TCP')
        key = f"{ip}:{port}:{slave}" if ct == "TCP" else f"{ip}:{slave}"
        if key in self.workers and self.workers[key].isRunning():
            return
        worker = ModbusWorker(dev, self)
        worker.data_received.connect(self._on_data_received)
        worker.log_message.connect(self._on_log_message)
        worker.alert_triggered.connect(self._on_alert_triggered)
        worker.start()
        self.workers[key] = worker

    def stop_device(self, dev: dict):
        ip, port, slave = dev['ip'], dev['port'], dev.get('slave_id', 1)
        ct  = dev.get('conn_type', 'TCP')
        key = f"{ip}:{port}:{slave}" if ct == "TCP" else f"{ip}:{slave}"
        if key in self.workers:
            self.workers[key].stop()

    def refresh_device(self, dev: dict):
        ip, port, slave = dev['ip'], dev['port'], dev.get('slave_id', 1)
        ct  = dev.get('conn_type', 'TCP')
        key = f"{ip}:{port}:{slave}" if ct == "TCP" else f"{ip}:{slave}"
        if key in self.workers:
            self.workers[key].trigger_refresh()

    def start_all_devices(self):
        for dev in self.devices:
            self.start_device(dev)

    def stop_all_devices(self):
        for w in self.workers.values():
            w.stop()

    def set_selected_graph(self, val_id: str, name: str):
        self.selected_graph_lid  = val_id
        self.selected_graph_name = name
        if "live_data" in self._views:
            self._views["live_data"].set_graph_target(val_id, name)

    # ═════════════════════════════════════════════════════════════════
    # SIGNALS
    # ═════════════════════════════════════════════════════════════════
    @pyqtSlot(str, str)
    def _on_data_received(self, val_id: str, value: str):
        self.live_values[val_id] = value
        try:
            self.data_history.setdefault(val_id, []).append(float(value))
            if len(self.data_history[val_id]) > 600:
                self.data_history[val_id] = self.data_history[val_id][-600:]
        except:
            pass
        if "live_data" in self._views:
            self._views["live_data"].on_data_received(val_id, value)

    @pyqtSlot(str)
    def _on_log_message(self, msg: str):
        ts  = datetime.now().strftime("%H:%M:%S")
        sno = len(self.global_log) + 1
        
        node = ""
        dev_name = ""
        field_name = ""
        addr = ""
        data_reading = msg
        unit = ""
        dtype = ""

        # Parse message format: "[node] message"
        if msg.startswith("[") and "] " in msg:
            parts = msg.split("] ", 1)
            node = parts[0][1:]
            rest = parts[1]
            data_reading = rest

            # Look up configured device info
            matched_dev = None
            for d in self.devices:
                ip = d.get("ip", "")
                port = d.get("port", 502)
                slave = d.get("slave_id", 1)
                ct = d.get("conn_type", "TCP")
                d_key = f"{ip}:{port}:{slave}" if ct == "TCP" else f"{ip}:{slave}"
                if d_key == node:
                    matched_dev = d
                    dev_name = d.get("device_name", "")
                    break

            # Check if this is a register reading/event
            import re
            reg_match = re.search(r'(?:Reg|@|Reg\s+)\s*(\d+)', rest)
            if reg_match:
                addr = reg_match.group(1)
                if matched_dev:
                    field_name = matched_dev.get("names", {}).get(addr, f"REG {addr}")
                    unit = matched_dev.get("units", {}).get(addr, "")
                    dtype = matched_dev.get("types", {}).get(addr, "FLOAT32")

        entry = (sno, dev_name, node, field_name, addr, data_reading, unit, dtype, ts)
        self.global_log.append(entry)
        if len(self.global_log) > 2000:
            self.global_log = self.global_log[-2000:]
        if "live_data" in self._views:
            self._views["live_data"].append_log(msg)
        if "live_log" in self._views:
            self._views["live_log"].add_log_entry(entry)

    @pyqtSlot(dict, float)
    def _on_alert_triggered(self, alert: dict, value: float):
        key = f"{alert.get('device_ip')}:{alert.get('reg')}"
        now = datetime.now()
        with self.alert_lock:
            last = self.alert_cooldowns.get(key)
            if last is None or (now - last).seconds >= 300:
                self.alert_cooldowns[key] = now
                self._send_alert_email(alert, value)
                write_alarm_history_csv(
                    alert.get('dev_name', ''), alert.get('field_name', ''),
                    alert.get('reg', ''), value,
                    alert.get('condition', ''), alert.get('threshold', '')
                )

    def _send_alert_email(self, alert: dict, value: float):
        import smtplib, ssl
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        if not self.email_settings.get('email_enabled', True):
            return
        try:
            s   = self.email_settings
            msg = MIMEMultipart()
            msg["From"]    = s.get('sender_email', '')
            msg["To"]      = s.get('recipient_email', '')
            msg["Subject"] = s.get('subject', 'THE LOGGER Alert')
            body = (
                f"ALERT TRIGGERED\n\nDevice: {alert.get('dev_name','')}\n"
                f"Field: {alert.get('field_name','')}\n"
                f"Value: {value} {alert.get('condition','')} {alert.get('threshold','')}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            msg.attach(MIMEText(body, "plain"))
            ctx = ssl.create_default_context()
            with smtplib.SMTP(s.get('smtp_server', ''), int(s.get('smtp_port', 587)), timeout=15) as srv:
                srv.starttls(context=ctx)
                srv.login(s.get('sender_email', ''), s.get('sender_password', ''))
                srv.sendmail(s.get('sender_email', ''), s.get('recipient_email', ''), msg.as_string())
            write_email_log_csv(alert.get('dev_name', ''), alert.get('field_name', ''),
                                s.get('recipient_email', ''), "SUCCESS")
        except Exception as e:
            write_email_log_csv(alert.get('dev_name', ''), alert.get('field_name', ''),
                                self.email_settings.get('recipient_email', ''), f"FAIL: {e}")

    @pyqtSlot(list)
    def _on_devices_changed(self, devices):
        self.devices = devices; save_devices(devices)

    @pyqtSlot(dict)
    def _on_email_settings_saved(self, settings):
        self.email_settings = settings; save_email_settings(settings)

    @pyqtSlot(dict)
    def _on_users_changed(self, users):
        self.users = users; save_users(users)

    # ═════════════════════════════════════════════════════════════════
    # PDF EXPORT
    # ═════════════════════════════════════════════════════════════════
    def export_pdf(self):
        if not HAS_REPORTLAB:
            QMessageBox.critical(self, "Error",
                "reportlab not found.\nInstall: pip install reportlab"); return
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            reports_dir = os.path.join(DATA_PATH, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            target = os.path.join(reports_dir,
                f"DailyLog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

            c = rl_canvas.Canvas(target, pagesize=landscape(letter))
            w, h = landscape(letter)

            def draw_header(page_num):
                c.setFillColorRGB(0.97, 0.97, 0.98); c.rect(0, 0, w, h, fill=1)
                c.setFillColorRGB(0.82, 0.18, 0.18)
                c.setFont("Helvetica-Bold", 20); c.drawString(40, h - 46, "THE LOGGER")
                c.setFillColorRGB(0.2, 0.2, 0.2)
                c.setFont("Helvetica", 9)
                c.drawString(40, h - 64, f"Daily Log  |  {date_str}  |  Page {page_num}")
                c.setStrokeColorRGB(0.82, 0.18, 0.18)
                c.setLineWidth(1.5); c.line(40, h - 72, w - 40, h - 72)
                c.setFont("Helvetica-Bold", 8); c.setFillColorRGB(0.37, 0.42, 0.53)
                for txt, x in [("S.NO",40),("DEVICE",85),("IP",210),("FIELD",330),
                                ("ADDR",470),("VALUE",525),("UNIT",615),("TYPE",665),("TIME",725)]:
                    c.drawString(x, h - 90, txt)
                c.setLineWidth(0.5); c.line(40, h - 96, w - 40, h - 96)
                return h - 110

            page = 1; y = draw_header(page)
            for i, entry in enumerate(self.global_log):
                if y < 50:
                    c.showPage(); page += 1; y = draw_header(page)
                c.setFillColorRGB(0.1, 0.1, 0.1); c.setFont("Helvetica", 8)
                for val, x in zip(entry, [40, 85, 210, 330, 470, 525, 615, 665, 725]):
                    c.drawString(x, y, str(val)[:25])
                y -= 13
            c.save()
            QMessageBox.information(self, "Exported", f"Daily log saved:\n{target}")
            webbrowser.open(target)
        except Exception as ex:
            QMessageBox.critical(self, "Error", str(ex))

    def _export_alarm_csv(self):
        date_str = datetime.now().strftime("%Y-%m-%d")
        src = os.path.join(DATA_PATH, "live", f"Alarm_History_{date_str}.csv")
        if not os.path.exists(src):
            QMessageBox.warning(self, "No Data", "No alarm history for today."); return
        dst, _ = QFileDialog.getSaveFileName(self, "Save", f"Alarm_History_{date_str}.csv", "CSV (*.csv)")
        if dst:
            shutil.copy2(src, dst)
            QMessageBox.information(self, "Exported", f"Saved to:\n{dst}")

    # ═════════════════════════════════════════════════════════════════
    # PERIODIC / LOGOUT / CLOSE
    # ═════════════════════════════════════════════════════════════════
    def _periodic_refresh(self):
        if self.active_view == "add_device" and "add_device" in self._views:
            running = {k for k, w in self.workers.items() if w.isRunning()}
            self._views["add_device"].refresh_status(running)

    def _logout(self):
        for w in self.workers.values():
            w.stop()
        self.close()
        from .auth_views import show_login_flow
        show_login_flow()

    def closeEvent(self, event):
        for w in self.workers.values():
            w.stop()
        event.accept()
