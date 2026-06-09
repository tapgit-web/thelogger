"""
trends_view.py  —  Historic Trend Analytics (PyQtGraph)
"""
import os, csv
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFrame, QCheckBox, QScrollArea,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg

from ..backend.core import DATA_PATH, load_trend_settings, save_trend_settings
from .icons import btn_icon

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import letter, landscape
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


PALETTE = ["#10B981", "#28A745", "#4285F4", "#F29900", "#6F42C1", "#E83E8C", "#20C997", "#FD7E14"]


class TrendsView(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app             = app
        self.trend_settings  = load_trend_settings()
        self.selected_lids   = []
        self.pivoted_data    = {}
        self.timestamps_list = []
        self.reg_vars: list[tuple[int, QCheckBox]] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # ---- Selection bar ----
        sel_frame = QFrame()
        sel_frame.setStyleSheet("QFrame#sel_frame { background-color:#FFFFFF; border:1px solid #E4E6EB; border-radius:8px; }")
        sel_frame.setObjectName("sel_frame")
        sf_layout = QVBoxLayout(sel_frame)
        sf_layout.setContentsMargins(16, 12, 16, 12)
        sf_layout.setSpacing(8)

        # Row 1: device + registers
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("NODE"))
        self.dev_cb = QComboBox()
        dev_opts = [d.get('device_name') or f"{d['ip']}@{d.get('slave_id',1)}" for d in self.app.devices]
        self.dev_cb.addItems(dev_opts)
        self.dev_cb.currentIndexChanged.connect(self._on_dev_change)
        r1.addWidget(self.dev_cb)
        r1.addSpacing(16)
        r1.addWidget(QLabel("PARAMETERS"))

        # Scrollable checkbox area for registers
        self.reg_scroll = QScrollArea()
        self.reg_scroll.setWidgetResizable(True)
        self.reg_scroll.setFixedHeight(68)
        self.reg_scroll.setFixedWidth(340)
        self.reg_scroll.setStyleSheet("QScrollArea { border: 1px solid #E4E6EB; border-radius:4px; background:#F0F2F5; }")
        self.reg_inner = QWidget(); self.reg_inner.setStyleSheet(".QWidget { background-color:#F0F2F5; }")
        self.reg_layout = QHBoxLayout(self.reg_inner)
        self.reg_layout.setContentsMargins(4, 4, 4, 4)
        self.reg_scroll.setWidget(self.reg_inner)
        r1.addWidget(self.reg_scroll)

        btn_all = QPushButton("SET ALL")
        btn_all.setObjectName("blue_btn")
        btn_all.setFixedHeight(30)
        btn_all.clicked.connect(self._select_all_regs)
        r1.addWidget(btn_all)
        r1.addStretch()
        sf_layout.addLayout(r1)

        # Row 2: date range
        r2 = QHBoxLayout()
        now = datetime.now()
        sod = now.replace(hour=0, minute=0, second=0)

        for lbl_txt, default_dt, attr in [("FROM", sod, "from_dt"), ("TO", now, "to_dt")]:
            r2.addWidget(QLabel(lbl_txt))
            selectors = {}
            for unit, fmt, vals in [
                ("y", "%Y", [str(y) for y in range(2024, 2031)]),
                ("m", "%m", [f"{i:02d}" for i in range(1,13)]),
                ("d", "%d", [f"{i:02d}" for i in range(1,32)]),
                ("h", "%H", [f"{i:02d}" for i in range(0,24)]),
                ("min","%M",[f"{i:02d}" for i in range(0,60)]),
            ]:
                cb = QComboBox(); cb.addItems(vals); cb.setCurrentText(default_dt.strftime(fmt))
                cb.setFixedWidth(72 if unit=="y" else 58)
                cb.setStyleSheet("""
                    QComboBox {
                        background-color: #FFFFFF;
                        color: #172B4D;
                        border: 1.5px solid #DFE1E6;
                        border-radius: 4px;
                        padding: 3px 4px 3px 6px;
                        font-size: 9pt;
                        font-weight: 500;
                    }
                    QComboBox:focus { border-color: #10B981; }
                    QComboBox::drop-down {
                        border: none;
                        width: 14px;
                    }
                    QComboBox QAbstractItemView {
                        background-color: #FFFFFF;
                        color: #172B4D;
                        selection-background-color: #ECFDF5;
                        selection-color: #10B981;
                    }
                """)
                r2.addWidget(cb)
                selectors[unit] = cb
            if lbl_txt == "FROM": self.from_dt = selectors
            else:                  self.to_dt   = selectors
            r2.addSpacing(10)

        btn_refresh = QPushButton("  Refresh View")
        btn_refresh.setObjectName("blue_btn")
        btn_refresh.setIcon(btn_icon("refresh"))
        from PyQt6.QtCore import QSize as _QS
        btn_refresh.setIconSize(_QS(13, 13))
        btn_refresh.clicked.connect(self.sync_trend)
        btn_refresh.setFixedHeight(30)
        r2.addWidget(btn_refresh)
        r2.addStretch()
        sf_layout.addLayout(r2)

        # Row 3: limits + PDF
        r3 = QHBoxLayout()
        r3.addWidget(QLabel("LOW LIMIT"))
        self.low_limit = QLineEdit(self.trend_settings.get("low_limit", ""))
        self.low_limit.setFixedWidth(80)
        r3.addWidget(self.low_limit)
        r3.addWidget(QLabel("UPPER LIMIT"))
        self.high_limit = QLineEdit(self.trend_settings.get("upper_limit", ""))
        self.high_limit.setFixedWidth(80)
        r3.addWidget(self.high_limit)
        r3.addWidget(QLabel("CONDITION"))
        self.cond_cb = QComboBox()
        self.cond_cb.addItems(["Both Limits","Upper Limit Only","Low Limit Only","No Limits"])
        self.cond_cb.setCurrentText(self.trend_settings.get("visible_condition","Both Limits"))
        r3.addWidget(self.cond_cb)
        r3.addWidget(QLabel("DECIMALS"))
        self.dec_cb = QComboBox(); self.dec_cb.addItems(["0","1","2","3","4"])
        self.dec_cb.setCurrentText(self.trend_settings.get("decimal_places","3"))
        r3.addWidget(self.dec_cb)
        r3.addStretch()
        btn_pdf = QPushButton("  Export PDF")
        btn_pdf.setObjectName("dark_btn")
        from PyQt6.QtCore import QSize as _QS2
        btn_pdf.setIcon(btn_icon("pdf"))
        btn_pdf.setIconSize(_QS2(13, 13))
        btn_pdf.setFixedHeight(30)
        btn_pdf.clicked.connect(self.export_pdf)
        r3.addWidget(btn_pdf)
        sf_layout.addLayout(r3)

        layout.addWidget(sel_frame)

        # ---- Tabs: Graph / Table / Bar ----
        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)

        # Graph tab
        graph_tab = QWidget()
        gt_layout = QVBoxLayout(graph_tab); gt_layout.setContentsMargins(4, 4, 4, 4)
        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget(background="#F0F2F5")
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.addLegend(offset=(10, 10))
        self.plot.getAxis('left').setPen(pg.mkPen('#65676B'))
        self.plot.getAxis('bottom').setPen(pg.mkPen('#65676B'))
        self.plot.getAxis('left').setTextPen(pg.mkPen('#65676B'))
        self.plot.getAxis('bottom').setTextPen(pg.mkPen('#65676B'))
        gt_layout.addWidget(self.plot)
        tabs.addTab(graph_tab, " GRAPH VIEW ")

        # Table tab
        table_tab = QWidget()
        tt_layout = QVBoxLayout(table_tab); tt_layout.setContentsMargins(4, 4, 4, 4)
        self.data_table = QTreeWidget()
        self.data_table.setRootIsDecorated(False)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tt_layout.addWidget(self.data_table)
        tabs.addTab(table_tab, " DATA TABLE ")

        # Bar tab
        bar_tab = QWidget()
        bt_layout = QVBoxLayout(bar_tab); bt_layout.setContentsMargins(4, 4, 4, 4)
        self.bar_plot = pg.PlotWidget(background="#F0F2F5")
        self.bar_plot.showGrid(x=False, y=True, alpha=0.2)
        bt_layout.addWidget(self.bar_plot)
        tabs.addTab(bar_tab, " BAR CHART ")

        # Init device
        if self.app.devices:
            self._on_dev_change(0)

    # ------------------------------------------------------------------
    def _on_dev_change(self, idx):
        # Clear register checkboxes
        for i in reversed(range(self.reg_layout.count())):
            self.reg_layout.itemAt(i).widget().deleteLater()
        self.reg_vars.clear()
        if idx < 0 or idx >= len(self.app.devices):
            return
        dev = self.app.devices[idx]
        for reg in dev['registers']:
            name = dev.get('names', {}).get(str(reg), f"REG {reg}")
            cb = QCheckBox(name)
            cb.stateChanged.connect(self.sync_trend)
            self.reg_layout.addWidget(cb)
            self.reg_vars.append((reg, cb))
        if self.reg_vars:
            self.reg_vars[0][1].setChecked(True)

    def _select_all_regs(self):
        for _, cb in self.reg_vars:
            cb.setChecked(True)

    def _get_date(self, selectors: dict) -> datetime:
        try:
            return datetime.strptime(
                f"{selectors['y'].currentText()}-{selectors['m'].currentText()}-"
                f"{selectors['d'].currentText()} {selectors['h'].currentText()}:"
                f"{selectors['min'].currentText()}:00", "%Y-%m-%d %H:%M:%S"
            )
        except:
            return datetime.min

    # ------------------------------------------------------------------
    def sync_trend(self):
        self._save_settings()
        idx = self.dev_cb.currentIndex()
        if idx < 0 or idx >= len(self.app.devices):
            return
        dev       = self.app.devices[idx]
        ip, port  = dev['ip'], dev['port']
        slave     = dev.get('slave_id', 1)
        f_dt      = self._get_date(self.from_dt)
        t_dt      = self._get_date(self.to_dt)

        selected_regs = {reg: cb for reg, cb in self.reg_vars if cb.isChecked()}
        if not selected_regs:
            return

        self.selected_lids = [
            f"{ip}:{port}:{slave}:{reg}" for reg in selected_regs
        ]
        target_regs = {str(reg) for reg in selected_regs}

        prefix   = f"{ip.replace('.','_')}_{port}_s{slave}"
        live_dir = os.path.join(DATA_PATH, "live")
        all_files = sorted([
            os.path.join(live_dir, f)
            for f in os.listdir(live_dir)
            if f.startswith(prefix) and f.endswith(".csv")
        ]) if os.path.exists(live_dir) else []

        self.pivoted_data = {}
        for fname in all_files:
            try:
                with open(fname) as f:
                    reader = csv.reader(f); next(reader)
                    for row in reader:
                        if len(row) > 5 and str(row[4]) in target_regs:
                            try:
                                dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                                if f_dt <= dt <= t_dt:
                                    ts = row[0]; r_addr = str(row[4]); val = float(row[5])
                                    self.pivoted_data.setdefault(ts, {})[r_addr] = val
                            except: pass
            except: continue

        self.timestamps_list = sorted(self.pivoted_data.keys())[-300:]
        for lid in self.selected_lids:
            r_addr = lid.split(":")[-1]
            self.app.data_history[lid] = [self.pivoted_data[ts].get(r_addr, 0.0) for ts in self.timestamps_list]

        addr_to_name = {str(reg): dev.get('names',{}).get(str(reg), f"REG {reg}") for reg in selected_regs}
        self._draw_graph(selected_regs, addr_to_name)
        self._draw_bar(selected_regs, addr_to_name)
        self._update_table(target_regs, addr_to_name)

    # ------------------------------------------------------------------
    def _draw_graph(self, selected_regs, addr_to_name):
        self.plot.clear()
        prec = int(self.dec_cb.currentText())
        ts   = self.timestamps_list
        if not ts: return

        for i, (reg, cb) in enumerate([(r, c) for r, c in self.reg_vars if c.isChecked()]):
            lid  = f"{self.app.devices[self.dev_cb.currentIndex()]['ip']}:{self.app.devices[self.dev_cb.currentIndex()]['port']}:{self.app.devices[self.dev_cb.currentIndex()].get('slave_id',1)}:{reg}"
            data = self.app.data_history.get(lid, [])
            if not data: continue
            color = PALETTE[i % len(PALETTE)]
            pen = pg.mkPen(color=color, width=2)
            name = addr_to_name.get(str(reg), f"REG {reg}")
            self.plot.plot(list(range(len(data))), data, pen=pen, name=name)

        # Limit lines
        try:
            lo = self.low_limit.text().strip(); hi = self.high_limit.text().strip()
            cond = self.cond_cb.currentText()
            if lo and cond in ["Both Limits","Low Limit Only"]:
                self.plot.addLine(y=float(lo), pen=pg.mkPen('#10B981', width=1.5, style=Qt.PenStyle.DashLine))
            if hi and cond in ["Both Limits","Upper Limit Only"]:
                self.plot.addLine(y=float(hi), pen=pg.mkPen('#D35400', width=1.5, style=Qt.PenStyle.DashLine))
        except: pass

    def _draw_bar(self, selected_regs, addr_to_name):
        self.bar_plot.clear()
        dev = self.app.devices[self.dev_cb.currentIndex()]
        ip, port, slave = dev['ip'], dev['port'], dev.get('slave_id', 1)
        bar_w = 0.7 / max(len(selected_regs), 1)
        for i, (reg, cb) in enumerate([(r,c) for r,c in self.reg_vars if c.isChecked()]):
            lid  = f"{ip}:{port}:{slave}:{reg}"
            data = self.app.data_history.get(lid, [])
            if not data: continue
            color = PALETTE[i % len(PALETTE)]
            x = [j + i * bar_w for j in range(len(data))]
            bg = pg.BarGraphItem(x=x, height=data, width=bar_w * 0.9, brush=color, pen='w')
            self.bar_plot.addItem(bg)

    def _update_table(self, target_regs, addr_to_name):
        sorted_addrs = sorted(target_regs)
        self.data_table.setColumnCount(1 + len(sorted_addrs))
        self.data_table.setHeaderLabels(["TIMESTAMP"] + [addr_to_name.get(a, a) for a in sorted_addrs])
        self.data_table.clear()
        prec = int(self.dec_cb.currentText())
        for ts in sorted(self.pivoted_data.keys(), reverse=True)[:1000]:
            row_vals = [ts]
            all_zero = True
            for addr in sorted_addrs:
                val = self.pivoted_data[ts].get(addr)
                if val is not None:
                    row_vals.append(f"{val:.{prec}f}")
                    if val != 0: all_zero = False
                else:
                    row_vals.append("---")
            if all_zero and any(self.pivoted_data[ts].get(a) is not None for a in sorted_addrs):
                continue
            self.data_table.addTopLevelItem(QTreeWidgetItem(row_vals))

    def _save_settings(self):
        self.trend_settings.update({
            "low_limit": self.low_limit.text().strip(),
            "upper_limit": self.high_limit.text().strip(),
            "visible_condition": self.cond_cb.currentText(),
            "decimal_places": self.dec_cb.currentText()
        })
        save_trend_settings(self.trend_settings)

    def export_pdf(self):
        if not HAS_REPORTLAB:
            QMessageBox.critical(self, "Error", "reportlab not installed."); return
        export_dir = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not export_dir: return
        try:
            dev   = self.app.devices[self.dev_cb.currentIndex()]
            alias = (dev.get('device_name') or dev['ip']).replace(' ','_')
            fn    = os.path.join(export_dir, f"TrendReport_{alias}_{datetime.now().strftime('%H%M%S')}.pdf")
            c = rl_canvas.Canvas(fn, pagesize=landscape(letter))
            w, h = landscape(letter)
            c.setFont("Helvetica-Bold", 18); c.setFillColorRGB(0, 0.36, 0.72)
            c.drawString(40, h-50, "THE LOGGER — TREND REPORT")
            c.setFont("Helvetica", 9); c.setFillColorRGB(0.4,0.4,0.4)
            c.drawString(40, h-70, f"Device: {alias}  |  Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            c.save()
            QMessageBox.information(self, "Exported", f"Saved to:\n{fn}")
            import webbrowser; webbrowser.open(fn)
        except Exception as ex:
            QMessageBox.critical(self, "Error", str(ex))
