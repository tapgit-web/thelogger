"""
other_views.py
Remaining PyQt6 views:
  - LiveLogView         (System Analytics / Live Log)
  - AlarmConfigView     (Email Alerts + SMTP Config)
  - DataExportView      (CSV / PDF Export)
  - UserManagerView     (User management)
"""
from .icons import btn_icon, icon

import os, csv, shutil, hashlib
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QFrame, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QTextEdit, QGroupBox, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QColor, QFont

# =====================================================================
# LIVE LOG VIEW
# =====================================================================

class LiveLogView(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)

        # Toolbar
        from PyQt6.QtCore import QSize
        bar = QHBoxLayout()
        ICON_SIZE = QSize(13, 13)
        # Buttons where text must be black (coloured backgrounds reduce contrast)
        BLACK_TEXT = {" Alarm History", " PDF Export"}
        for text, alias, obj, slot in [
            (" Open Folder",    "folder",     "blue_btn",    self._open_folder),
            (" Alarm History",  "alarm_hist", "warning_btn", lambda: self.app.navigate("email_alerts")),
            (" Email Logs",     "email",      "blue_btn",    lambda: self.app.navigate("email_logs_view")),
            (" PDF Export",     "pdf",        "dark_btn",    self.app.export_pdf),
        ]:
            btn = QPushButton(text)
            if obj:
                btn.setObjectName(obj)
            btn.setIcon(btn_icon(alias))
            btn.setIconSize(ICON_SIZE)
            btn.clicked.connect(slot)
            if text in BLACK_TEXT:
                btn.setStyleSheet("color: #000000; font-weight: 600;")
            bar.addWidget(btn)
        bar.addStretch()
        layout.addLayout(bar)

        # Log table
        self.tree = QTreeWidget()
        self.tree.setColumnCount(9)
        self.tree.setHeaderLabels(["S.NO","DEVICE NAME","NODE","FIELD NAME","ADDR","DATA READING","UNIT","TYPE","TIMESTAMP"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tree)

        self._load_existing_logs()

    def _open_folder(self):
        import webbrowser
        from ..backend.core import DATA_PATH
        webbrowser.open(os.path.join(DATA_PATH, "live"))

    def _load_existing_logs(self):
        for entry in self.app.global_log[-100:]:
            self._add_row(entry)

    @pyqtSlot(tuple)
    def add_log_entry(self, entry: tuple):
        self._add_row(entry)

    def _add_row(self, entry):
        item = QTreeWidgetItem([str(v) for v in entry])
        # Highlight error rows
        if any(k in str(entry[5]) for k in ["FAILURE:", "ALERT:", "Error"]):
            for col in range(item.columnCount()):
                item.setForeground(col, QColor("#34D399"))
                item.setFont(col, QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.tree.addTopLevelItem(item)
        self.tree.scrollToBottom()


# =====================================================================
# ALARM CONFIG VIEW
# =====================================================================

class AlarmConfigView(QWidget):
    settings_saved = pyqtSignal(dict)

    def __init__(self, email_settings: dict, devices: list, current_user: str, users: dict, parent=None):
        super().__init__(parent)
        self.email_settings = email_settings
        self.devices  = devices
        self.user     = current_user
        self.users    = users
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ---- Tab 1: SMTP / Server Config ----
        perms = self.users.get(self.user, {}).get("permissions", [])
        if self.user == "admin" or "email_smtp_config" in perms:
            smtp_tab = QWidget()
            smtp_tab.setStyleSheet(".QWidget { background-color: #FFFFFF; }")
            s_layout = QVBoxLayout(smtp_tab)
            s_layout.setContentsMargins(20, 20, 20, 20)
            s_layout.setSpacing(10)

            s = self.email_settings
            form = QFormLayout()
            form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

            def fld(lbl, initial="", pw=False):
                e = QLineEdit(str(initial))
                if pw: e.setEchoMode(QLineEdit.EchoMode.Password)
                lbl_w = QLabel(lbl); lbl_w.setStyleSheet("color: #65676B; font-size: 8pt; font-weight: bold; background: transparent;")
                form.addRow(lbl_w, e)
                return e

            self.smtp_server    = fld("SMTP SERVER",         s.get("smtp_server", ""))
            self.smtp_port      = fld("SMTP PORT",           s.get("smtp_port", "587"))
            self.sender_email   = fld("SENDER EMAIL",        s.get("sender_email", ""))
            self.sender_pass    = fld("APP PASSWORD",        s.get("sender_password", ""), pw=True)
            self.recipient_email= fld("RECIPIENT EMAIL",     s.get("recipient_email", ""))
            self.email_subject  = fld("SUBJECT",             s.get("subject", "THE LOGGER Alert"))

            self.email_enabled_cb = QCheckBox("EMAIL ALERTS ENABLED")
            self.email_enabled_cb.setChecked(s.get("email_enabled", True))

            s_layout.addLayout(form)
            s_layout.addWidget(self.email_enabled_cb)

            btn_row = QHBoxLayout()
            from PyQt6.QtCore import QSize as _QS
            btn_save = QPushButton(" Save SMTP Config")
            btn_save.setObjectName("blue_btn")
            btn_save.setIcon(btn_icon("save"))
            btn_save.setIconSize(_QS(13, 13))
            btn_save.clicked.connect(self._save_smtp)
            btn_test = QPushButton(" Send Test Email")
            btn_test.setObjectName("warning_btn")
            btn_test.setIcon(btn_icon("test_email"))
            btn_test.setIconSize(_QS(13, 13))
            btn_test.clicked.connect(self._send_test_email)
            btn_row.addWidget(btn_save)
            btn_row.addWidget(btn_test)
            btn_row.addStretch()
            s_layout.addLayout(btn_row)
            s_layout.addStretch()

            tabs.addTab(smtp_tab, " SMTP CONFIG ")

        # ---- Tab 2: Alert Rules ----
        alert_tab = QWidget()
        alert_tab.setStyleSheet(".QWidget { background-color: #FFFFFF; }")
        a_layout = QVBoxLayout(alert_tab)
        a_layout.setContentsMargins(20, 20, 20, 20)
        a_layout.setSpacing(8)

        # Alert rule form
        rule_frame = QFrame()
        rule_frame.setStyleSheet(".QFrame { background-color: #F0F2F5; border-radius: 6px; }")
        rule_lay = QHBoxLayout(rule_frame)
        rule_lay.setContentsMargins(12, 8, 12, 8)

        self.alert_dev_cb   = QComboBox()
        self.alert_reg_cb   = QComboBox()
        self.alert_cond_cb  = QComboBox(); self.alert_cond_cb.addItems([">", "<", "=="])
        self.alert_thresh   = QLineEdit(); self.alert_thresh.setPlaceholderText("Threshold")
        self.alert_thresh.setFixedWidth(100)

        dev_options = [d.get('device_name') or f"{d['ip']}@{d.get('slave_id',1)}" for d in self.devices]
        self.alert_dev_cb.addItems(dev_options)
        self.alert_dev_cb.currentIndexChanged.connect(self._on_alert_dev_change)
        if self.devices:
            self._on_alert_dev_change(0)

        for lbl_text, widget in [("DEVICE", self.alert_dev_cb), ("REGISTER", self.alert_reg_cb),
                                   ("CONDITION", self.alert_cond_cb), ("THRESHOLD", self.alert_thresh)]:
            lbl = QLabel(lbl_text); lbl.setStyleSheet("color:#65676B; font-size:8pt; font-weight:bold; background:transparent;")
            rule_lay.addWidget(lbl); rule_lay.addWidget(widget)

        from PyQt6.QtCore import QSize as _QS2
        btn_add_alert = QPushButton(" Add Rule")
        btn_add_alert.setObjectName("blue_btn")
        btn_add_alert.setIcon(btn_icon("add_rule"))
        btn_add_alert.setIconSize(_QS2(13, 13))
        btn_add_alert.clicked.connect(self._add_alert_rule)
        rule_lay.addWidget(btn_add_alert)
        a_layout.addWidget(rule_frame)

        # Alert rules table
        self.alert_table = QTreeWidget()
        self.alert_table.setColumnCount(6)
        self.alert_table.setHeaderLabels(["DEVICE","SLAVE","REGISTER","CONDITION","THRESHOLD","ACTION"])
        self.alert_table.setRootIsDecorated(False)
        self.alert_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        a_layout.addWidget(self.alert_table)

        from PyQt6.QtCore import QSize as _QS3
        btn_del_alert = QPushButton(" Remove Selected Rule")
        btn_del_alert.setObjectName("danger_btn")
        btn_del_alert.setIcon(btn_icon("delete"))
        btn_del_alert.setIconSize(_QS3(13, 13))
        btn_del_alert.clicked.connect(self._delete_alert_rule)
        a_layout.addWidget(btn_del_alert)

        tabs.addTab(alert_tab, " ALERT RULES ")

        self._refresh_alert_table()

    # ------------------------------------------------------------------
    def _on_alert_dev_change(self, idx):
        self.alert_reg_cb.clear()
        if idx < 0 or idx >= len(self.devices):
            return
        dev = self.devices[idx]
        for reg in dev['registers']:
            name = dev.get('names', {}).get(str(reg), f"REG {reg}")
            self.alert_reg_cb.addItem(f"{name} [{reg}]", reg)

    def _add_alert_rule(self):
        idx = self.alert_dev_cb.currentIndex()
        if idx < 0 or idx >= len(self.devices):
            return
        dev = self.devices[idx]
        reg_idx = self.alert_reg_cb.currentIndex()
        if reg_idx < 0:
            return
        reg = self.alert_reg_cb.itemData(reg_idx)
        reg_name = dev.get('names', {}).get(str(reg), f"REG {reg}")
        cond  = self.alert_cond_cb.currentText()
        thresh = self.alert_thresh.text().strip()
        if not thresh:
            QMessageBox.warning(self, "Warning", "Enter a threshold value.")
            return

        alert = {
            "device_ip": dev['ip'],
            "port":      dev['port'],
            "slave_id":  dev.get('slave_id', 1),
            "reg":       reg,
            "field_name": reg_name,
            "dev_name":  dev.get('device_name', dev['ip']),
            "condition": cond,
            "threshold": thresh
        }
        self.email_settings.setdefault('alerts', []).append(alert)
        self._refresh_alert_table()
        self.settings_saved.emit(self.email_settings)

    def _delete_alert_rule(self):
        sel = self.alert_table.selectedItems()
        if not sel:
            return
        row = self.alert_table.currentIndex().row()
        top = self.alert_table.topLevelItem(row)
        if not top:
            return
        idx = top.data(0, Qt.ItemDataRole.UserRole)
        alerts = self.email_settings.get('alerts', [])
        if 0 <= idx < len(alerts):
            alerts.pop(idx)
            self._refresh_alert_table()
            self.settings_saved.emit(self.email_settings)

    def _refresh_alert_table(self):
        self.alert_table.clear()
        for i, alert in enumerate(self.email_settings.get('alerts', [])):
            item = QTreeWidgetItem([
                str(alert.get('dev_name', alert.get('device_ip',''))),
                str(alert.get('slave_id', 1)),
                str(alert.get('field_name', alert.get('reg',''))),
                str(alert.get('condition', '')),
                str(alert.get('threshold', '')),
                "DELETE"
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, i)
            self.alert_table.addTopLevelItem(item)

    def _save_smtp(self):
        self.email_settings.update({
            "smtp_server":    self.smtp_server.text().strip(),
            "smtp_port":      self.smtp_port.text().strip(),
            "sender_email":   self.sender_email.text().strip(),
            "sender_password":self.sender_pass.text().strip(),
            "recipient_email":self.recipient_email.text().strip(),
            "subject":        self.email_subject.text().strip(),
            "email_enabled":  self.email_enabled_cb.isChecked(),
        })
        self.settings_saved.emit(self.email_settings)
        QMessageBox.information(self, "Saved", "SMTP configuration saved.")

    def _send_test_email(self):
        import smtplib, ssl
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        try:
            msg = MIMEMultipart()
            msg["From"]    = self.sender_email.text()
            msg["To"]      = self.recipient_email.text()
            msg["Subject"] = "[TEST] THE LOGGER Email Alert"
            msg.attach(MIMEText("This is a test email from THE LOGGER monitoring system.", "plain"))

            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server.text(), int(self.smtp_port.text()), timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(self.sender_email.text(), self.sender_pass.text())
                server.sendmail(self.sender_email.text(), self.recipient_email.text(), msg.as_string())
            QMessageBox.information(self, "Success", "Test email sent successfully!")
        except Exception as ex:
            QMessageBox.critical(self, "Failed", f"Could not send email:\n{ex}")


# =====================================================================
# DATA EXPORT VIEW
# =====================================================================

class DataExportView(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(16)

        title = QLabel("DATA EXPORT CENTER")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1C1E21; background: transparent;")
        layout.addWidget(title)

        desc = QLabel(
            "Export today's live data, historical trends, and alarm logs.\n"
            "CSV files are stored in the live/ folder. PDF reports are generated on demand."
        )
        desc.setStyleSheet("color: #65676B; background: transparent;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Export cards
        cards_row = QHBoxLayout()

        from PyQt6.QtCore import QSize as _QS4
        def card(title_txt, desc_txt, btn_txt, btn_alias, btn_slot, btn_obj=""):
            frame = QGroupBox(title_txt)
            frame.setMinimumWidth(200)
            fl = QVBoxLayout(frame)
            d = QLabel(desc_txt)
            d.setWordWrap(True)
            d.setStyleSheet("color:#5E6C84; background:transparent; font-size:9pt;")
            btn = QPushButton(f"  {btn_txt}")
            if btn_obj: btn.setObjectName(btn_obj)
            btn.setIcon(btn_icon(btn_alias))
            btn.setIconSize(_QS4(13, 13))
            btn.clicked.connect(btn_slot)
            fl.addWidget(d)
            fl.addStretch()
            fl.addWidget(btn)
            return frame

        cards_row.addWidget(card(
            "Full Daily Log PDF",
            "Generate a PDF report of all today's live readings from every configured device.",
            "Export Daily PDF", "pdf", self.app.export_pdf, "dark_btn"
        ))
        cards_row.addWidget(card(
            "Open Live Data Folder",
            "Open the folder containing all daily CSV log files for direct access.",
            "Open Folder", "folder", self._open_folder, "neutral_btn"
        ))
        cards_row.addWidget(card(
            "Alarm History CSV",
            "Export today's alarm trigger history as a CSV file.",
            "Export Alarm CSV", "alarm_hist", self._export_alarm_csv, "warning_btn"
        ))
        cards_row.addWidget(card(
            "Email Logs CSV",
            "Export the log of all emails sent today as a CSV file.",
            "Export Email Logs", "email", self._export_email_logs, "success_btn"
        ))
        layout.addLayout(cards_row)
        layout.addStretch()

    def _open_folder(self):
        import webbrowser
        from ..backend.core import DATA_PATH
        webbrowser.open(os.path.join(DATA_PATH, "live"))

    def _export_alarm_csv(self):
        from ..backend.core import DATA_PATH
        date_str = datetime.now().strftime("%Y-%m-%d")
        src = os.path.join(DATA_PATH, "live", f"Alarm_History_{date_str}.csv")
        if not os.path.exists(src):
            QMessageBox.warning(self, "No Data", "No alarm history found for today."); return
        dst, _ = QFileDialog.getSaveFileName(self, "Save Alarm CSV", f"Alarm_History_{date_str}.csv", "CSV Files (*.csv)")
        if dst:
            shutil.copy2(src, dst)
            QMessageBox.information(self, "Exported", f"Saved to:\n{dst}")

    def _export_email_logs(self):
        from ..backend.core import DATA_PATH
        date_str = datetime.now().strftime("%Y-%m-%d")
        src = os.path.join(DATA_PATH, "live", f"Email_Logs_{date_str}.csv")
        if not os.path.exists(src):
            QMessageBox.warning(self, "No Data", "No email logs found for today."); return
        dst, _ = QFileDialog.getSaveFileName(self, "Save Email Logs CSV", f"Email_Logs_{date_str}.csv", "CSV Files (*.csv)")
        if dst:
            shutil.copy2(src, dst)
            QMessageBox.information(self, "Exported", f"Saved to:\n{dst}")


# =====================================================================
# USER MANAGER VIEW
# =====================================================================

class UserManagerView(QWidget):
    users_changed = pyqtSignal(dict)

    ALL_PERMS = [
        ("live_data",       "Live Dashboard"),
        ("add_device",      "Device Manager"),
        ("live_log",        "Live Log"),
        ("email_config",    "Alarm Config"),
        ("email_smtp_config","SMTP Config"),
        ("export_data",     "Data Export"),
        ("data_trends",     "Historic Trends"),
        ("user_manager",    "User Manager"),
    ]

    def __init__(self, users: dict, parent=None):
        super().__init__(parent)
        self.users = users
        self._setup_ui()

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        # Left: Add/Edit form
        left = QFrame()
        left.setFixedWidth(300)
        left.setStyleSheet(".QFrame { background-color: #FFFFFF; border: 1px solid #E4E6EB; border-radius: 8px; }")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(20, 20, 20, 20)

        title = QLabel("ADD / EDIT USER")
        title.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12pt; background: transparent;")
        ll.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.u_name = QLineEdit(); self.u_name.setPlaceholderText("username")
        self.u_pass = QLineEdit(); self.u_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.u_pass.setPlaceholderText("Leave blank to keep existing")
        lbl_n = QLabel("USERNAME"); lbl_n.setStyleSheet("color:#65676B; font-size:8pt; font-weight:bold; background:transparent;")
        lbl_p = QLabel("PASSWORD"); lbl_p.setStyleSheet("color:#65676B; font-size:8pt; font-weight:bold; background:transparent;")
        form.addRow(lbl_n, self.u_name)
        form.addRow(lbl_p, self.u_pass)
        ll.addLayout(form)

        perm_lbl = QLabel("PERMISSIONS")
        perm_lbl.setStyleSheet("color: #65676B; font-size: 8pt; font-weight: bold; margin-top: 10px; background: transparent;")
        ll.addWidget(perm_lbl)

        self.perm_checks: dict[str, QCheckBox] = {}
        for pid, pname in self.ALL_PERMS:
            cb = QCheckBox(pname)
            cb.setChecked(pid != "user_manager")
            self.perm_checks[pid] = cb
            ll.addWidget(cb)

        from PyQt6.QtCore import QSize as _QS5
        btn_create = QPushButton(" Create / Update User")
        btn_create.setObjectName("blue_btn")
        btn_create.setIcon(btn_icon("check"))
        btn_create.setIconSize(_QS5(13, 13))
        btn_create.clicked.connect(self._save_user)
        ll.addSpacing(10)
        ll.addWidget(btn_create)
        ll.addStretch()

        # Right: User table
        right = QFrame()
        right.setStyleSheet(".QFrame { background-color: #F0F2F5; }")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)

        r_title = QLabel("ACTIVE SYSTEM USERS")
        r_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #1C1E21; background: transparent; margin-bottom: 8px;")
        rl.addWidget(r_title)

        self.user_table = QTreeWidget()
        self.user_table.setColumnCount(3)
        self.user_table.setHeaderLabels(["USERNAME", "PERMISSIONS", "TYPE"])
        self.user_table.setRootIsDecorated(False)
        self.user_table.setAlternatingRowColors(True)
        self.user_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.itemClicked.connect(self._on_user_click)
        rl.addWidget(self.user_table)

        from PyQt6.QtCore import QSize as _QS6
        btn_del = QPushButton(" Remove Selected User")
        btn_del.setObjectName("danger_btn")
        btn_del.setIcon(btn_icon("delete"))
        btn_del.setIconSize(_QS6(13, 13))
        btn_del.clicked.connect(self._delete_user)
        rl.addWidget(btn_del)

        root.addWidget(left)
        root.addWidget(right, stretch=1)
        self._refresh_table()

    def _save_user(self):
        uname = self.u_name.text().lower().strip()
        upass = self.u_pass.text().strip()
        if not uname:
            QMessageBox.critical(self, "Error", "Username is required."); return

        is_update = uname in self.users
        if is_update:
            if not QMessageBox.question(self, "Update", f"Update user '{uname}'?") == QMessageBox.StandardButton.Yes:
                return
        elif not upass:
            QMessageBox.critical(self, "Error", "Password is required for new users."); return

        hashed = hashlib.sha256(upass.encode()).hexdigest() if upass else self.users.get(uname, {}).get("password", "")
        perms  = [pid for pid, cb in self.perm_checks.items() if cb.isChecked()]
        is_adm = self.users.get(uname, {}).get("is_admin", False) if is_update else (uname == "admin")

        self.users[uname] = {"password": hashed, "permissions": perms, "is_admin": is_adm}
        self._refresh_table()
        self.users_changed.emit(self.users)
        self.u_name.clear(); self.u_pass.clear()
        QMessageBox.information(self, "Saved", f"User '{uname}' {'updated' if is_update else 'created'}.")

    def _delete_user(self):
        sel = self.user_table.selectedItems()
        if not sel: return
        uname = self.user_table.currentItem().text(0).lower()
        if uname == "admin":
            QMessageBox.critical(self, "Error", "Cannot remove primary admin."); return
        if QMessageBox.question(self, "Confirm", f"Remove user '{uname}'?") == QMessageBox.StandardButton.Yes:
            self.users.pop(uname, None)
            self._refresh_table()
            self.users_changed.emit(self.users)

    def _on_user_click(self, item, col):
        uname = item.text(0).lower()
        if uname not in self.users: return
        udata = self.users[uname]
        self.u_name.setText(uname)
        self.u_pass.clear()
        up = udata.get("permissions", [])
        for pid, cb in self.perm_checks.items():
            cb.setChecked(pid in up)

    def _refresh_table(self):
        self.user_table.clear()
        for uname, udata in self.users.items():
            perms = ", ".join(udata.get("permissions", []))
            utype = "ADMIN" if udata.get("is_admin") else "OPERATOR"
            item = QTreeWidgetItem([uname.upper(), perms, utype])
            self.user_table.addTopLevelItem(item)
