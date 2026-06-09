"""
auth_views.py  —  Activation, Splash, Login screens
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon
import os, hashlib

from ..backend.core import (
    load_local_license, save_local_license, check_license_online,
    get_hwid, load_users, resource_path
)
from .icons import btn_icon, icon


# =====================================================================
def show_login_flow():
    """Entry point: show activation or splash depending on license."""
    app = QApplication.instance() or QApplication(sys.argv)

    # Load stylesheet
    qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
    if os.path.exists(qss_path):
        with open(qss_path) as f:
            app.setStyleSheet(f.read())

    if load_local_license():
        splash = SplashScreen()
        splash.show()
    else:
        act = ActivationWindow()
        act.show()

    sys.exit(app.exec())


# =====================================================================
class ActivationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("THE LOGGER — Activation")
        self.setFixedSize(460, 320)
        self.setStyleSheet(".QWidget { background-color: #F0F2F5; }")
        self._center()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet("""
            QFrame { background: #FFFFFF; border-radius: 12px; }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(14)

        title = QLabel("SYSTEM LOCKED")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #10B981; font-size: 16pt; font-weight: bold; background: transparent;")

        sub = QLabel("ONLINE ACTIVATION REQUIRED")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #65676B; font-size: 9pt; background: transparent;")

        hwid_box = QFrame()
        hwid_box.setStyleSheet(".QFrame { background-color: #F0F2F5; border-radius: 6px; }")
        hwid_layout = QHBoxLayout(hwid_box)
        hwid_layout.setContentsMargins(12, 8, 12, 8)
        hwid_lbl = QLabel(f"DEVICE HWID: {get_hwid()}")
        hwid_lbl.setStyleSheet("color: #10B981; font-family: Consolas; font-size: 9pt; background: transparent;")
        hwid_layout.addWidget(hwid_lbl)

        key_lbl = QLabel("License Key")
        key_lbl.setStyleSheet(
            "color:#5E6C84; font-size:8pt; font-weight:600; background:transparent;"
        )

        self.key_entry = QLineEdit()
        self.key_entry.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_entry.returnPressed.connect(self._activate)

        self.btn = QPushButton("  Activate System")
        self.btn.setObjectName("blue_btn")
        self.btn.setIcon(btn_icon("activate"))
        self.btn.setIconSize(QSize(14, 14))
        self.btn.clicked.connect(self._activate)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: #10B981; background: transparent;")

        card_layout.addWidget(title)
        card_layout.addWidget(sub)
        card_layout.addWidget(hwid_box)
        card_layout.addWidget(key_lbl)
        card_layout.addWidget(self.key_entry)
        card_layout.addWidget(self.btn)
        card_layout.addWidget(self.status_lbl)

        layout.addWidget(card)

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def _activate(self):
        key = self.key_entry.text().strip().upper()
        if not key:
            self.status_lbl.setText("Please enter a license key.")
            return
        self.btn.setText("VERIFYING..."); self.btn.setEnabled(False)
        QApplication.processEvents()
        valid, msg = check_license_online(key)
        if valid:
            save_local_license(key)
            self.close()
            splash = SplashScreen()
            splash.show()
        else:
            self.status_lbl.setText(f"❌ {msg}")
            self.btn.setText("ACTIVATE SYSTEM"); self.btn.setEnabled(True)


# =====================================================================
class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setFixedSize(480, 280)
        self.setStyleSheet(".QWidget { background-color: #FFFFFF; border-radius: 14px; }")
        self._center()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 40, 50, 40)
        layout.setSpacing(16)

        # Logo
        # icon_p = resource_path("icon.png")
        # if os.path.exists(icon_p):
        #     logo_lbl = QLabel()
        #     pix = QPixmap(icon_p).scaled(90, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        #     logo_lbl.setPixmap(pix)
        #     logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #     logo_lbl.setStyleSheet("background: transparent;")
        #     layout.addWidget(logo_lbl)

        title = QLabel()
        title_p = resource_path("the_logger_text_logo.png")
        if os.path.exists(title_p):
            pix2 = QPixmap(title_p).scaled(300, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            title.setPixmap(pix2)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("background: transparent;")
        else:
            title.setText(
                "<span style='font-family:\"Buongiorno_Rastellino\", \"Buongiorno_Rastellino Script\";'>THE</span> "
                "<span style='font-family:\"Josefin Sans\";'>LOGGER</span>"
            )
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("color: #10B981; font-size: 32pt; font-weight: bold; background: transparent;")
        layout.addWidget(title)

        self.status_lbl = QLabel("INITIALIZING SYSTEM...")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: #65676B; font-size: 9pt; background: transparent;")
        layout.addWidget(self.status_lbl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar { background: #E4E6EB; border-radius: 3px; border: none; }
            QProgressBar::chunk { background: #10B981; border-radius: 3px; }
        """)
        layout.addWidget(self.progress)

        self._val = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(20)

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def _advance(self):
        self._val += 2
        self.progress.setValue(self._val)
        if self._val == 40:
            self.status_lbl.setText("CONNECTING TO CORE...")
        elif self._val == 75:
            self.status_lbl.setText("LOADING DEVICE CONFIGS...")
        if self._val >= 100:
            self._timer.stop()
            self.close()
            self._show_login()

    def _show_login(self):
        self._login = LoginWindow()
        self._login.show()


# =====================================================================
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("THE LOGGER — Secure Access")
        self.setFixedSize(420, 340)
        self.setStyleSheet(".QWidget { background-color: #F0F2F5; }")
        self._center()

        icon_p = resource_path("icon.png")
        if os.path.exists(icon_p):
            self.setWindowIcon(QIcon(icon_p))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet("QFrame { background: #FFFFFF; border-radius: 12px; }")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40, 36, 40, 36)
        cl.setSpacing(14)

        title = QLabel("SECURE ACCESS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #1C1E21; font-size: 16pt; font-weight: bold; background: transparent;")

        def fld(lbl_txt, pw=False):
            f = QFrame(); f.setStyleSheet("background: transparent;")
            fl = QVBoxLayout(f); fl.setContentsMargins(0, 0, 0, 0); fl.setSpacing(2)
            lbl = QLabel(lbl_txt); lbl.setStyleSheet("color: #65676B; font-size: 8pt; font-weight: bold; background: transparent;")
            e = QLineEdit()
            if pw: e.setEchoMode(QLineEdit.EchoMode.Password)
            fl.addWidget(lbl); fl.addWidget(e)
            return f, e

        u_frame, self.u_entry = fld("SYSTEM OPERATOR")
        self.u_entry.setText("ADMIN")
        p_frame, self.p_entry = fld("PASSCODE", pw=True)
        self.p_entry.returnPressed.connect(self._login)

        btn = QPushButton("  Authenticate")
        btn.setObjectName("blue_btn")
        btn.setFixedHeight(42)
        btn.setIcon(btn_icon("authenticate"))
        btn.setIconSize(QSize(15, 15))
        btn.clicked.connect(self._login)

        self.err_lbl = QLabel("")
        self.err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.err_lbl.setStyleSheet("color: #10B981; background: transparent;")

        cl.addWidget(title)
        cl.addWidget(u_frame)
        cl.addWidget(p_frame)
        cl.addWidget(btn)
        cl.addWidget(self.err_lbl)
        layout.addWidget(card)
        self.p_entry.setFocus()

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def _login(self):
        uname = self.u_entry.text().lower().strip()
        pwd   = self.p_entry.text()
        users = load_users()
        h     = hashlib.sha256(pwd.encode()).hexdigest()
        if uname in users and users[uname]["password"] == h:
            self.close()
            from .main_window import MainWindow
            self._main = MainWindow(uname)
            self._main.show()
        else:
            self.err_lbl.setText("ACCESS DENIED: INVALID CREDENTIALS")
            self.p_entry.clear()
