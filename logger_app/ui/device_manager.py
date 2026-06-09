"""
device_manager.py  —  Add / Edit / Delete Modbus Devices
"""

import serial.tools.list_ports

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QRadioButton, QButtonGroup, QFrame,
    QTreeWidget, QTreeWidgetItem, QSizePolicy, QMessageBox, QFileDialog,
    QHeaderView, QGroupBox, QScrollArea, QSplitter, QTableWidget,
    QTableWidgetItem, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont

import json
from .icons import btn_icon


DATA_TYPES = [
    "FLOAT32", "INT32", "UINT32",
    "DOUBLE INTEGER", "UNSIGNED DOUBLE INTEGER",
    "INT16", "UINT16", "BCD", "UNSIGNED INT"
]
REGISTER_MODES = [
    "Input Register (FC04)",
    "Holding Register (FC03)",
    "Input Coil (FC02)",
    "Output Coil (FC01)"
]
REGISTER_MODES_MAP = {
    "Input Register (FC04)": "FC04",
    "Holding Register (FC03)": "FC03",
    "Input Coil (FC02)": "FC02",
    "Output Coil (FC01)": "FC01",
    "FC04": "Input Register (FC04)",
    "FC03": "Holding Register (FC03)",
    "FC02": "Input Coil (FC02)",
    "FC01": "Output Coil (FC01)",
}
DEFAULT_REGISTER_NAMES = [
    "Voltage R", "Voltage Y", "Voltage B",
    "Current R", "Current Y", "Current B",
    "Power Factor", "Frequency", "Active Power", "Reactive Power",
    "Temperature"
]
DEFAULT_REGISTER_UNITS = ["V", "V", "V", "A", "A", "A", "PF", "Hz", "kW", "kVAR", "°C"]
COMMON_UNITS = ["V", "A", "Hz", "kW", "kVAR", "kWh", "PF", "%", "°C", "m³/h", "bar"]
BAUDRATES  = ["9600", "19200", "38400", "57600", "115200"]
PARITIES   = ["N", "E", "O", "S", "M"]
STOPBITS   = ["1", "1.5", "2"]
BYTESIZES  = ["8", "7", "6", "5"]

class NoScrollComboBox(QComboBox):
    def wheelEvent(self, e):
        e.ignore()



def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("config_section_title")
    return lbl


def _field(label: str, widget: QWidget, parent_layout: QFormLayout):
    lbl = QLabel(label)
    lbl.setObjectName("field_label")
    parent_layout.addRow(lbl, widget)
    return widget


class DeviceManagerView(QWidget):
    """Left panel = form, Right panel = device table."""

    devices_changed = pyqtSignal(list)   # emitted when device list is modified

    def __init__(self, devices: list, running_keys: set, parent=None):
        super().__init__(parent)
        self.devices     = devices
        self.running_keys = running_keys
        self.edit_index   = None
        self._reg_rows: list[dict] = []   # pending registers in the mini table
        self._setup_ui()
        self._refresh_table()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # ---- Left form panel wrapper ----
        left_panel = QFrame()
        left_panel.setObjectName("panel_frame")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setMinimumWidth(500)
        form_scroll.setMaximumWidth(580)
        form_scroll.setStyleSheet("QScrollArea { border: none; background: #F4F5F7; }")

        form_widget = QWidget()
        form_widget.setStyleSheet(".QWidget { background-color: #F4F5F7; }")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(20)

        # ── HEADER CARD ────────────────────────────────────────────────
        header_card = QFrame()
        header_card.setObjectName("form_card")
        h_lay = QHBoxLayout(header_card)
        h_lay.setContentsMargins(15, 10, 15, 10)
        
        self.form_title = QLabel("NODE CONFIG")
        self.form_title.setStyleSheet("color: #172B4D; font-weight: 800; font-size: 13pt;")
        
        btn_new = QPushButton("  New Node")
        btn_new.setObjectName("blue_btn")
        btn_new.setIcon(btn_icon("new"))
        btn_new.setIconSize(QSize(14, 14))
        btn_new.setFixedHeight(32)
        btn_new.clicked.connect(self._clear_form)

        h_lay.addWidget(self.form_title)
        h_lay.addStretch()
        h_lay.addWidget(btn_new)
        form_layout.addWidget(header_card)

        # ── BASIC INFO CARD ────────────────────────────────────────────
        info_card = QFrame()
        info_card.setObjectName("form_card")
        info_lay = QVBoxLayout(info_card)
        info_lay.setContentsMargins(20, 20, 20, 20)
        info_lay.setSpacing(15)

        info_lay.addWidget(_section_label("GENERAL IDENTIFICATION"))
        
        self.entry_name = QLineEdit()
        self.entry_name.setPlaceholderText("e.g. Main Distribution Board")
        flay1 = QFormLayout()
        flay1.setSpacing(8)
        _field("DEVICE ALIAS / NAME", self.entry_name, flay1)
        info_lay.addLayout(flay1)

        info_lay.addWidget(_section_label("CONNECTION PROTOCOL"))
        ct_row = QHBoxLayout()
        self.rb_tcp    = QRadioButton("MODBUS TCP")
        self.rb_serial = QRadioButton("MODBUS SERIAL")
        self.rb_tcp.setChecked(True)
        self.rb_tcp.toggled.connect(self._toggle_conn)
        ct_row.addWidget(self.rb_tcp)
        ct_row.addWidget(self.rb_serial)
        ct_row.addStretch()
        info_lay.addLayout(ct_row)

        # TCP fields
        self.tcp_frame = QFrame()
        tlay = QFormLayout(self.tcp_frame)
        tlay.setContentsMargins(0, 0, 0, 0)
        tlay.setSpacing(8)
        self.entry_ip   = QLineEdit(); self.entry_ip.setPlaceholderText("192.168.1.100")
        self.entry_port = QLineEdit("502")
        self.entry_slave = QLineEdit("1")
        _field("IP ADDRESS",  self.entry_ip,    tlay)
        _field("PORT",        self.entry_port,  tlay)
        _field("SLAVE ID(s)", self.entry_slave, tlay)
        info_lay.addWidget(self.tcp_frame)

        # Serial fields
        self.serial_frame = QFrame()
        self.serial_frame.setVisible(False)
        slay = QFormLayout(self.serial_frame)
        slay.setContentsMargins(0, 0, 0, 0)
        slay.setSpacing(8)
        self.entry_comport = QLineEdit(); self.entry_comport.setPlaceholderText("COM1")
        self.entry_baudrate = NoScrollComboBox(); self.entry_baudrate.addItems(BAUDRATES); self.entry_baudrate.setCurrentText("9600")
        self.entry_parity   = NoScrollComboBox(); self.entry_parity.addItems(PARITIES)
        self.entry_stopbits = NoScrollComboBox(); self.entry_stopbits.addItems(STOPBITS)
        self.entry_bytesize = NoScrollComboBox(); self.entry_bytesize.addItems(BYTESIZES)
        self.entry_method   = NoScrollComboBox(); self.entry_method.addItems(["rtu", "ascii"])
        self.entry_slave_s  = QLineEdit("1")
        _field("COM PORT",  self.entry_comport,  slay)
        _field("BAUD RATE", self.entry_baudrate, slay)
        _field("PARITY",    self.entry_parity,   slay)
        _field("STOP BITS", self.entry_stopbits, slay)
        _field("BYTE SIZE", self.entry_bytesize, slay)
        _field("METHOD",    self.entry_method,   slay)
        _field("SLAVE ID",  self.entry_slave_s,  slay)
        info_lay.addWidget(self.serial_frame)
        
        form_layout.addWidget(info_card)

        # ── REGISTER MAPPING CARD ──────────────────────────────────────
        reg_card = QFrame()
        reg_card.setObjectName("form_card")
        reg_lay = QVBoxLayout(reg_card)
        reg_lay.setContentsMargins(20, 20, 20, 20)
        reg_lay.setSpacing(15)

        reg_lay.addWidget(_section_label("REGISTER CONFIGURATION"))

        reg_input_card = QFrame()
        reg_input_card.setObjectName("reg_input_container")
        reg_input_lay = QVBoxLayout(reg_input_card)
        reg_input_lay.setContentsMargins(15, 15, 15, 15)
        reg_input_lay.setSpacing(12)

        from PyQt6.QtWidgets import QGridLayout
        reg_grid = QGridLayout()
        reg_grid.setSpacing(10)

        def _flbl(txt):
            l = QLabel(txt)
            l.setObjectName("field_label")
            return l

        self.entry_reg_addr = QLineEdit()
        self.entry_reg_addr.setPlaceholderText("e.g. 3000")

        self.entry_reg_name = NoScrollComboBox()
        self.entry_reg_name.setEditable(True)
        self.entry_reg_name.addItems([""] + DEFAULT_REGISTER_NAMES)
        self.entry_reg_name.currentTextChanged.connect(self._auto_fill_unit)

        self.entry_reg_unit = NoScrollComboBox()
        self.entry_reg_unit.setEditable(True)
        self.entry_reg_unit.addItems([""] + COMMON_UNITS)

        reg_grid.addWidget(_flbl("ADDRESS"),         0, 0)
        reg_grid.addWidget(self.entry_reg_addr,      1, 0)
        reg_grid.addWidget(_flbl("PARAMETER NAME"),  0, 1, 1, 2)
        reg_grid.addWidget(self.entry_reg_name,      1, 1, 1, 2)
        reg_grid.addWidget(_flbl("UNIT"),            0, 3)
        reg_grid.addWidget(self.entry_reg_unit,      1, 3)

        self.entry_reg_type = NoScrollComboBox()
        self.entry_reg_type.addItems(DATA_TYPES)
        reg_grid.addWidget(_flbl("DATA TYPE"),       2, 0, 1, 4)
        reg_grid.addWidget(self.entry_reg_type,      3, 0, 1, 4)

        self.entry_reg_op = NoScrollComboBox()
        self.entry_reg_op.addItems(["/", "*"])
        self.entry_reg_factor = QLineEdit("1")
        self.entry_reg_prec = NoScrollComboBox()
        self.entry_reg_prec.addItems(["1", "0.1", "0.01", "0.001", "0.0001", "0.00001"])
        self.entry_reg_prec.setCurrentText("0.1")
        self.entry_reg_prec.setToolTip(
            "Decimal scale factor: raw value is multiplied by this.\n"
            "0.1 → 1 decimal place, 0.01 → 2, 0.001 → 3, etc."
        )

        reg_grid.addWidget(_flbl("MATH OP"),        4, 0)
        reg_grid.addWidget(self.entry_reg_op,       5, 0)
        reg_grid.addWidget(_flbl("SCALE FACTOR"),   4, 1)
        reg_grid.addWidget(self.entry_reg_factor,   5, 1)
        reg_grid.addWidget(_flbl("DECIMALS"),       4, 2, 1, 2)
        reg_grid.addWidget(self.entry_reg_prec,     5, 2, 1, 2)

        self.entry_reg_mode = NoScrollComboBox()
        self.entry_reg_mode.addItems(REGISTER_MODES)
        reg_grid.addWidget(_flbl("REGISTER TYPE (FUNCTION CODE)"), 6, 0, 1, 4)
        reg_grid.addWidget(self.entry_reg_mode,      7, 0, 1, 4)

        reg_grid.setColumnStretch(0, 1)
        reg_grid.setColumnStretch(1, 2)
        reg_grid.setColumnStretch(2, 1)
        reg_grid.setColumnStretch(3, 1)

        reg_input_lay.addLayout(reg_grid)
        
        btn_add_reg = QPushButton("  Add Register to Table")
        btn_add_reg.setObjectName("blue_btn")
        btn_add_reg.setIcon(btn_icon("new"))
        btn_add_reg.setIconSize(QSize(14, 14))
        btn_add_reg.setFixedHeight(36)
        btn_add_reg.clicked.connect(self._add_reg_to_mini)
        reg_input_lay.addWidget(btn_add_reg)

        reg_lay.addWidget(reg_input_card)

        # Mini table area
        reg_lay.addWidget(_section_label("PENDING REGISTERS"))
        self.mini_table = QTableWidget(0, 7)
        self.mini_table.setHorizontalHeaderLabels(["ADDR", "NAME", "UNIT", "TYPE", "MATH", "DEC", "MODE"])
        self.mini_table.setFixedHeight(180)
        self.mini_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.mini_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.mini_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mini_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.mini_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.mini_table.doubleClicked.connect(self._prefill_reg_from_row)
        reg_lay.addWidget(self.mini_table)

        hint_lbl = QLabel("💡 Double-click a row to load it back into the form for editing, then re-add it.")
        hint_lbl.setStyleSheet("color:#5E6C84; font-size:7.5pt; font-style:italic; background:transparent;")
        hint_lbl.setWordWrap(True)
        reg_lay.addWidget(hint_lbl)

        btn_rm_reg = QPushButton("  Remove Selected Register")
        btn_rm_reg.setObjectName("danger_btn")
        btn_rm_reg.setIcon(btn_icon("delete"))
        btn_rm_reg.setIconSize(QSize(13, 13))
        btn_rm_reg.setFixedHeight(32)
        btn_rm_reg.clicked.connect(self._remove_mini_reg)
        reg_lay.addWidget(btn_rm_reg)

        form_layout.addWidget(reg_card)

        # ── ACTION BUTTONS ─────────────────────────────────────────────
        self.btn_save = QPushButton("  Save Node Configuration")
        self.btn_save.setObjectName("dark_btn")
        self.btn_save.setIcon(btn_icon("save"))
        self.btn_save.setIconSize(QSize(16, 16))
        self.btn_save.setFixedHeight(45)
        self.btn_save.setStyleSheet("font-size: 11pt;")
        self.btn_save.clicked.connect(self._save_device)
        form_layout.addWidget(self.btn_save)

        form_layout.addStretch()
        
        form_scroll.setWidget(form_widget)
        left_layout.addWidget(form_scroll)

        # ---- Right table panel ----
        right_panel = QFrame()
        right_panel.setStyleSheet(".QFrame { background-color: #F0F2F5; }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)

        table_title = QLabel("STORED DEVICES")
        table_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #1C1E21; background: transparent;")
        right_layout.addWidget(table_title)

        self.device_table = QTreeWidget()
        self.device_table.setColumnCount(11)
        self.device_table.setHeaderLabels([
            "ID", "DEVICE", "SLAVE", "REG NAME", "ADDRESS",
            "UNIT", "TYPE", "MATH", "MODE", "DEC", "STATE"
        ])
        self.device_table.setAlternatingRowColors(True)
        self.device_table.setRootIsDecorated(False)
        self.device_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.device_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.device_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        right_layout.addWidget(self.device_table)

        # Actions bar
        act_row = QHBoxLayout()
        ICON_S = QSize(13, 13)
        btn_dl   = QPushButton("  Download Config")
        btn_dl.setObjectName("dark_btn")
        btn_dl.setIcon(btn_icon("download")); btn_dl.setIconSize(ICON_S)
        btn_dl.clicked.connect(self._download_config)
        btn_ul   = QPushButton("  Upload Config")
        btn_ul.setObjectName("success_btn")
        btn_ul.setIcon(btn_icon("upload")); btn_ul.setIconSize(ICON_S)
        btn_ul.clicked.connect(self._upload_config)
        btn_edit = QPushButton("  Edit Node")
        btn_edit.setObjectName("warning_btn")
        btn_edit.setIcon(btn_icon("edit")); btn_edit.setIconSize(ICON_S)
        btn_edit.clicked.connect(self._load_edit)
        btn_del  = QPushButton("  Delete Node")
        btn_del.setObjectName("danger_btn")
        btn_del.setIcon(btn_icon("delete")); btn_del.setIconSize(ICON_S)
        btn_del.clicked.connect(self._delete_device)
        act_row.addWidget(btn_dl)
        act_row.addWidget(btn_ul)
        act_row.addStretch()
        act_row.addWidget(btn_edit)
        act_row.addWidget(btn_del)
        right_layout.addLayout(act_row)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter)

    # ------------------------------------------------------------------
    def _toggle_conn(self):
        is_tcp = self.rb_tcp.isChecked()
        self.tcp_frame.setVisible(is_tcp)
        self.serial_frame.setVisible(not is_tcp)

    def _auto_fill_unit(self, name: str):
        if name in DEFAULT_REGISTER_NAMES:
            idx = DEFAULT_REGISTER_NAMES.index(name)
            self.entry_reg_unit.setCurrentText(DEFAULT_REGISTER_UNITS[idx])
            self.entry_reg_type.setCurrentText("FLOAT32")

    def _add_reg_to_mini(self):
        addr = self.entry_reg_addr.text().strip()
        if not addr.isdigit():
            QMessageBox.warning(self, "Warning", "Enter a valid register address (integer).")
            return
        name  = self.entry_reg_name.currentText().strip()
        unit  = self.entry_reg_unit.currentText().strip()
        dtype = self.entry_reg_type.currentText()
        op    = self.entry_reg_op.currentText()
        fac   = self.entry_reg_factor.text().strip() or "1"
        prec  = self.entry_reg_prec.currentText()
        mode  = self.entry_reg_mode.currentText()
        math  = f"{op} {fac}"

        row = self.mini_table.rowCount()
        self.mini_table.insertRow(row)
        for col, val in enumerate([addr, name, unit, dtype, math, prec, mode]):
            self.mini_table.setItem(row, col, QTableWidgetItem(str(val)))

        self.entry_reg_addr.clear()

    def _prefill_reg_from_row(self, index):
        """Double-clicked a pending register row — load it back into the input form."""
        row = index.row()
        def cell(c):
            item = self.mini_table.item(row, c)
            return item.text() if item else ""

        self.entry_reg_addr.setText(cell(0))
        self.entry_reg_name.setCurrentText(cell(1))
        self.entry_reg_unit.setCurrentText(cell(2))
        self.entry_reg_type.setCurrentText(cell(3))
        math = cell(4)  # e.g. "/ 1"
        parts = math.split(" ") if " " in math else ["/", "1"]
        self.entry_reg_op.setCurrentText(parts[0])
        self.entry_reg_factor.setText(parts[1] if len(parts) > 1 else "1")
        dec_val = cell(5)
        if dec_val in [self.entry_reg_prec.itemText(i) for i in range(self.entry_reg_prec.count())]:
            self.entry_reg_prec.setCurrentText(dec_val)
        self.entry_reg_mode.setCurrentText(cell(6))
        # Remove the row so the user can re-add after editing
        self.mini_table.removeRow(row)

    def _remove_mini_reg(self):
        rows = {idx.row() for idx in self.mini_table.selectedIndexes()}
        for row in sorted(rows, reverse=True):
            self.mini_table.removeRow(row)

    def _clear_form(self):
        self.edit_index = None
        self.form_title.setText("NODE CONFIG")
        self.btn_save.setText("  Save Node")
        self.btn_save.setIcon(btn_icon("save"))
        self.btn_save.setObjectName("dark_btn")
        self.btn_save.style().unpolish(self.btn_save)
        self.btn_save.style().polish(self.btn_save)
        self.entry_name.clear()
        self.rb_tcp.setChecked(True)
        self.entry_ip.clear(); self.entry_port.setText("502"); self.entry_slave.setText("1")
        self.entry_reg_addr.clear(); self.entry_reg_name.setCurrentText("")
        self.entry_reg_unit.setCurrentText(""); self.entry_reg_type.setCurrentText("FLOAT32")
        self.entry_reg_op.setCurrentText("/"); self.entry_reg_factor.setText("1")
        self.entry_reg_prec.setCurrentText("0.1"); self.entry_reg_mode.setCurrentIndex(0)
        self.mini_table.setRowCount(0)

    def _save_device(self):
        is_tcp = self.rb_tcp.isChecked()
        conn_type = "TCP" if is_tcp else "SERIAL"
        ip = self.entry_ip.text().strip() if is_tcp else self.entry_comport.text().strip().upper()
        port_raw = self.entry_port.text().strip() if is_tcp else "0"
        slave_raw = self.entry_slave.text().strip() if is_tcp else self.entry_slave_s.text().strip()
        d_name = self.entry_name.text().strip()

        if not ip or not port_raw or self.mini_table.rowCount() == 0:
            QMessageBox.critical(self, "Error", "IP/Port and at least one register are required.")
            return

        try:
            port = int(port_raw)
            # Parse slave IDs
            if "-" in slave_raw:
                s, e = map(int, slave_raw.split("-"))
                slave_ids = list(range(s, e+1))
            elif "," in slave_raw:
                slave_ids = [int(x.strip()) for x in slave_raw.split(",") if x.strip()]
            else:
                slave_ids = [int(slave_raw)] if slave_raw else [1]

            rl, rn, ru, rt, rm, rop, rf, rdec = [], {}, {}, {}, {}, {}, {}, {}
            for row in range(self.mini_table.rowCount()):
                def cell(c): return self.mini_table.item(row, c).text() if self.mini_table.item(row, c) else ""
                addr  = cell(0); name_ = cell(1); unit_ = cell(2)
                dtype = cell(3); math  = cell(4); prec  = cell(5); mode_txt = cell(6)
                rl.append(int(addr))
                if name_: rn[addr] = name_
                if unit_: ru[addr] = unit_
                if dtype: rt[addr] = dtype
                rm[addr] = REGISTER_MODES_MAP.get(mode_txt, "FC04")
                rdec[addr] = prec
                parts = math.split(" ") if " " in math else ["/", "1"]
                rop[addr] = parts[0]; rf[addr] = parts[1] if len(parts) > 1 else "1"

            for i, sid in enumerate(slave_ids):
                fname = (f"{d_name} S{sid}" if len(slave_ids) > 1 and d_name else d_name)
                dev = {
                    "device_name": fname, "conn_type": conn_type,
                    "ip": ip, "port": port, "slave_id": sid,
                    "baudrate": self.entry_baudrate.currentText() if not is_tcp else "9600",
                    "parity":   self.entry_parity.currentText()   if not is_tcp else "N",
                    "stopbits": self.entry_stopbits.currentText() if not is_tcp else "1",
                    "bytesize": self.entry_bytesize.currentText() if not is_tcp else "8",
                    "method":   self.entry_method.currentText()   if not is_tcp else "rtu",
                    "registers": rl, "names": rn, "units": ru, "types": rt,
                    "modes": rm, "ops": rop, "factors": rf, "decimals": rdec
                }
                if self.edit_index is not None and i == 0:
                    if self.edit_index < len(self.devices):
                        self.devices[self.edit_index] = dev
                else:
                    exists = any(d['ip'] == ip and d['port'] == port and d.get('slave_id') == sid for d in self.devices)
                    if not exists:
                        self.devices.append(dev)

            self.edit_index = None
            self._clear_form()
            self._refresh_table()
            self.devices_changed.emit(self.devices)
            QMessageBox.information(self, "Saved", f"Added/Updated {len(slave_ids)} node(s) successfully.")

        except Exception as ex:
            QMessageBox.critical(self, "Error", f"Invalid data: {ex}")

    def _load_edit(self):
        sel = self.device_table.selectedItems()
        if not sel:
            return
        row = self.device_table.currentIndex().row()
        top = self.device_table.topLevelItem(row)
        if not top:
            return
        dev_idx = top.data(0, Qt.ItemDataRole.UserRole)
        if dev_idx is None:
            return

        self.edit_index = dev_idx
        d = self.devices[dev_idx]
        self.entry_name.setText(d.get('device_name', ''))
        ct = d.get('conn_type', 'TCP')
        self.rb_tcp.setChecked(ct == "TCP")
        self.rb_serial.setChecked(ct == "SERIAL")
        self._toggle_conn()
        if ct == "TCP":
            self.entry_ip.setText(d['ip'])
            self.entry_port.setText(str(d['port']))
            self.entry_slave.setText(str(d.get('slave_id', 1)))
        else:
            self.entry_comport.setText(d['ip'])
            self.entry_slave_s.setText(str(d.get('slave_id', 1)))
            self.entry_baudrate.setCurrentText(str(d.get('baudrate', '9600')))
            self.entry_parity.setCurrentText(d.get('parity', 'N'))

        self.mini_table.setRowCount(0)
        for reg in d['registers']:
            r = str(reg)
            op  = d.get('ops', {}).get(r, '/')
            fac = d.get('factors', {}).get(r, '1')
            mode_code = d.get('modes', {}).get(r, 'FC04')
            mode_txt  = REGISTER_MODES_MAP.get(mode_code, REGISTER_MODES[0])
            row_idx = self.mini_table.rowCount()
            self.mini_table.insertRow(row_idx)
            for col, val in enumerate([
                r, d.get('names', {}).get(r, ''), d.get('units', {}).get(r, ''),
                d.get('types', {}).get(r, 'FLOAT32'), f"{op} {fac}",
                d.get('decimals', {}).get(r, '2'), mode_txt
            ]):
                self.mini_table.setItem(row_idx, col, QTableWidgetItem(str(val)))

        self.form_title.setText("EDIT NODE")
        self.btn_save.setText("  Update Node")
        self.btn_save.setIcon(btn_icon("edit"))

    def _delete_device(self):
        sel = self.device_table.selectedItems()
        if not sel:
            return
        row = self.device_table.currentIndex().row()
        top = self.device_table.topLevelItem(row)
        if not top:
            return
        dev_idx = top.data(0, Qt.ItemDataRole.UserRole)
        if dev_idx is None:
            return
        if QMessageBox.question(self, "Confirm", "Remove entire device configuration?") == QMessageBox.StandardButton.Yes:
            self.devices.pop(dev_idx)
            self.edit_index = None
            self._refresh_table()
            self.devices_changed.emit(self.devices)

    def _refresh_table(self):
        self.device_table.clear()
        self.device_table.setHeaderLabels([
            "ID", "DEVICE", "SLAVE", "REG NAME", "ADDRESS",
            "UNIT", "TYPE", "MATH", "MODE", "DEC", "STATE"
        ])
        for idx, dev in enumerate(self.devices):
            ip    = dev['ip']
            port  = dev['port']
            slave = dev.get('slave_id', 1)
            ct    = dev.get('conn_type', 'TCP')
            key   = f"{ip}:{port}:{slave}" if ct == "TCP" else f"{ip}:{slave}"
            is_on = key in self.running_keys
            state = "ONLINE" if is_on else "OFFLINE"

            for reg in dev['registers']:
                r     = str(reg)
                name  = dev.get('names', {}).get(r, f"REG {reg}")
                unit  = dev.get('units', {}).get(r, "")
                dtype = dev.get('types', {}).get(r, "FLOAT32")
                op    = dev.get('ops', {}).get(r, "/")
                fac   = dev.get('factors', {}).get(r, "1")
                mode  = dev.get('modes', {}).get(r, "FC04")
                dec   = dev.get('decimals', {}).get(r, "2")
                dname = dev.get('device_name') or ip

                item = QTreeWidgetItem([
                    str(idx+1), f"{dname} [{ip}]", str(slave),
                    name, r, unit, dtype, f"{op} {fac}", mode, dec, state
                ])
                item.setData(0, Qt.ItemDataRole.UserRole, idx)
                if is_on:
                    for col in range(item.columnCount()):
                        item.setForeground(10, QColor("#28A745"))
                self.device_table.addTopLevelItem(item)

    def _download_config(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Download Config", "devices_config.json", "JSON Files (*.json)")
        if fname:
            from ..backend.core import load_devices
            with open(fname, "w") as f:
                json.dump(load_devices(), f, indent=4)
            QMessageBox.information(self, "Saved", f"Config downloaded to:\n{fname}")

    def _upload_config(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Upload Config", "", "JSON Files (*.json)")
        if not fname:
            return
        try:
            from ..backend.core import deobfuscate_data, save_devices
            with open(fname, "r") as f:
                content = f.read().strip()
            decoded = deobfuscate_data(content)
            new_devs = json.loads(decoded if decoded else content)
            if not isinstance(new_devs, list):
                raise ValueError("Expected a list.")
            if QMessageBox.question(self, "Confirm", "Overwrite current configuration?") == QMessageBox.StandardButton.Yes:
                save_devices(new_devs)
                self.devices.clear()
                self.devices.extend(new_devs)
                self._refresh_table()
                self.devices_changed.emit(self.devices)
                QMessageBox.information(self, "Success", "Configuration uploaded.")
        except Exception as ex:
            QMessageBox.critical(self, "Error", str(ex))

    def refresh_status(self, running_keys: set):
        self.running_keys = running_keys
        self._refresh_table()
