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
            
        if not self.pivoted_data:
            QMessageBox.warning(self, "No Data", "No historical data found for the selected date range and registers.")
            return

        export_dir = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not export_dir: return

        def draw_cell(canvas, text, x, y, width, height, align="left", bold=False, font_size=8):
            font_name = "Helvetica-Bold" if bold else "Helvetica"
            canvas.setFont(font_name, font_size)
            
            text_str = str(text)
            while canvas.stringWidth(text_str, font_name, font_size) > (width - 4) and len(text_str) > 3:
                text_str = text_str[:-4] + "..."
                
            if align == "right":
                canvas.drawRightString(x + width - 2, y + 3, text_str)
            elif align == "center":
                canvas.drawCentredString(x + width / 2, y + 3, text_str)
            else:
                canvas.drawString(x + 2, y + 3, text_str)

        try:
            dev   = self.app.devices[self.dev_cb.currentIndex()]
            alias = (dev.get('device_name') or dev['ip']).replace(' ','_')
            fn    = os.path.join(export_dir, f"TrendReport_{alias}_{datetime.now().strftime('%H%M%S')}.pdf")
            
            c = rl_canvas.Canvas(fn, pagesize=landscape(letter))
            w, h = landscape(letter)
            
            # --- PAGE 1: TITLE & GRAPH ---
            # Title Banner
            c.setFillColorRGB(0.06, 0.72, 0.51) # Theme Emerald Green
            c.rect(40, h - 70, w - 80, 40, fill=True, stroke=False)
            
            c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(55, h - 52, "THE LOGGER — HISTORIC TREND REPORT")
            
            # Metadata Box
            c.setFillColorRGB(0.94, 0.95, 0.96)
            c.rect(40, h - 145, w - 80, 65, fill=True, stroke=True)
            
            c.setFillColorRGB(0.1, 0.1, 0.1)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(60, h - 100, "Device:")
            c.drawString(60, h - 118, "Date Range:")
            c.drawString(60, h - 136, "Exported:")
            
            c.setFont("Helvetica", 9)
            f_dt_str = self._get_date(self.from_dt).strftime('%Y-%m-%d %H:%M:%S')
            t_dt_str = self._get_date(self.to_dt).strftime('%Y-%m-%d %H:%M:%S')
            dev_name = dev.get('device_name') or dev['ip']
            c.drawString(140, h - 100, f"{dev_name}")
            c.drawString(140, h - 118, f"{f_dt_str}   to   {t_dt_str}")
            c.drawString(140, h - 136, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            selected_regs = sorted([reg for reg, cb in self.reg_vars if cb.isChecked()])
            addr_to_name = {str(reg): dev.get('names', {}).get(str(reg), f"REG {reg}") for reg in selected_regs}

            c.setFont("Helvetica-Bold", 9)
            c.drawString(500, h - 100, "Total Parameters:")
            c.drawString(500, h - 118, "Total Records:")
            
            c.setFont("Helvetica", 9)
            c.drawString(610, h - 100, f"{len(selected_regs)}")
            c.drawString(610, h - 118, f"{len(self.pivoted_data)}")

            # --- PLOT AREA MATH & DIRECT VECTOR DRAWING ---
            x_min = 70
            x_max = w - 40 # 752
            y_min = 60
            y_max = h - 180 # 432
            W_plot = x_max - x_min # 682
            H_plot = y_max - y_min # 372
            
            # Draw plot area background
            c.setFillColorRGB(0.97, 0.97, 0.98)
            c.rect(x_min, y_min, W_plot, H_plot, fill=True, stroke=True)
            
            # Gather all values to compute Y scaling
            all_vals = []
            for reg in selected_regs:
                lid = f"{dev['ip']}:{dev['port']}:{dev.get('slave_id',1)}:{reg}"
                data = self.app.data_history.get(lid, [])
                if data:
                    all_vals.extend(data)
                    
            # Check limits
            lo_val = None
            hi_val = None
            cond = self.cond_cb.currentText()
            try:
                lo_str = self.low_limit.text().strip()
                if lo_str and cond in ["Both Limits", "Low Limit Only"]:
                    lo_val = float(lo_str)
                    all_vals.append(lo_val)
            except: pass
            try:
                hi_str = self.high_limit.text().strip()
                if hi_str and cond in ["Both Limits", "Upper Limit Only"]:
                    hi_val = float(hi_str)
                    all_vals.append(hi_val)
            except: pass
            
            if not all_vals:
                all_vals = [0.0, 100.0]
                
            min_y = min(all_vals)
            max_y = max(all_vals)
            if min_y == max_y:
                min_y -= 10
                max_y += 10
            else:
                # Add 10% padding to top/bottom
                padding = (max_y - min_y) * 0.1
                min_y -= padding
                max_y += padding
                
            # Draw Y-Axis grid lines & labels
            prec = int(self.dec_cb.currentText())
            c.setStrokeColorRGB(0.85, 0.85, 0.85)
            c.setLineWidth(0.5)
            c.setFont("Helvetica", 7)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            for i in range(5):
                y_val = min_y + i * (max_y - min_y) / 4
                sy = y_min + (i * H_plot / 4)
                c.line(x_min, sy, x_max, sy)
                c.drawRightString(x_min - 8, sy - 2.5, f"{y_val:.{prec}f}")
                
            # Draw X-Axis grid lines & labels
            t_count = len(self.timestamps_list)
            if t_count > 1:
                for i in range(5):
                    idx = int(i * (t_count - 1) / 4)
                    ts = self.timestamps_list[idx]
                    sx = x_min + (i * W_plot / 4)
                    c.line(sx, y_min, sx, y_max)
                    try:
                        time_str = ts.split(" ")[1] # HH:MM:SS
                    except:
                        time_str = ts
                    c.drawCentredString(sx, y_min - 12, time_str)
            else:
                c.line(x_min + W_plot/2, y_min, x_min + W_plot/2, y_max)
                c.drawCentredString(x_min + W_plot/2, y_min - 12, "00:00:00")
                
            # Draw Parameter Curves as Vector Paths
            for i, reg in enumerate(selected_regs):
                lid = f"{dev['ip']}:{dev['port']}:{dev.get('slave_id',1)}:{reg}"
                data = self.app.data_history.get(lid, [])
                if not data:
                    continue
                color_hex = PALETTE[i % len(PALETTE)]
                r_c = int(color_hex[1:3], 16) / 255.0
                g_c = int(color_hex[3:5], 16) / 255.0
                b_c = int(color_hex[5:7], 16) / 255.0
                
                c.setStrokeColorRGB(r_c, g_c, b_c)
                c.setLineWidth(1.5)
                
                path = c.beginPath()
                for idx, val in enumerate(data):
                    sx = x_min + (idx / max(t_count - 1, 1)) * W_plot
                    sy = y_min + ((val - min_y) / (max_y - min_y)) * H_plot
                    if idx == 0:
                        path.moveTo(sx, sy)
                    else:
                        path.lineTo(sx, sy)
                c.drawPath(path, stroke=True, fill=False)
                
            # Draw Limit Lines
            c.setLineWidth(1.0)
            if lo_val is not None:
                c.setStrokeColorRGB(0.06, 0.72, 0.51)
                c.setDash(4, 2)
                sy = y_min + ((lo_val - min_y) / (max_y - min_y)) * H_plot
                if y_min <= sy <= y_max:
                    c.line(x_min, sy, x_max, sy)
                    c.setFont("Helvetica-Bold", 7)
                    c.setFillColorRGB(0.06, 0.72, 0.51)
                    c.drawString(x_min + 10, sy + 3, f"Low Limit: {lo_val}")
                    
            if hi_val is not None:
                c.setStrokeColorRGB(0.83, 0.18, 0.18)
                c.setDash(4, 2)
                sy = y_min + ((hi_val - min_y) / (max_y - min_y)) * H_plot
                if y_min <= sy <= y_max:
                    c.line(x_min, sy, x_max, sy)
                    c.setFont("Helvetica-Bold", 7)
                    c.setFillColorRGB(0.83, 0.18, 0.18)
                    c.drawString(x_min + 10, sy + 3, f"Upper Limit: {hi_val}")
            c.setDash() # clear dash pattern
            
            # Chart Border overlay
            c.setStrokeColorRGB(0.4, 0.4, 0.4)
            c.setLineWidth(1.0)
            c.rect(x_min, y_min, W_plot, H_plot, fill=False, stroke=True)
            
            # Draw Chart Legend
            leg_x = x_min + 10
            leg_y = y_max + 8
            c.setFont("Helvetica-Bold", 7)
            for i, reg in enumerate(selected_regs):
                name = addr_to_name.get(str(reg), f"REG {reg}")
                color_hex = PALETTE[i % len(PALETTE)]
                r_c = int(color_hex[1:3], 16) / 255.0
                g_c = int(color_hex[3:5], 16) / 255.0
                b_c = int(color_hex[5:7], 16) / 255.0
                
                c.setStrokeColorRGB(r_c, g_c, b_c)
                c.setLineWidth(2.5)
                c.line(leg_x, leg_y + 2.5, leg_x + 15, leg_y + 2.5)
                
                c.setFillColorRGB(0.2, 0.2, 0.2)
                c.drawString(leg_x + 20, leg_y, name)
                
                text_w = c.stringWidth(name, "Helvetica-Bold", 7)
                leg_x += 20 + text_w + 20
                if leg_x > x_max - 50:
                    leg_x = x_min + 10
                    leg_y -= 10

            # --- PAGE 2+: DETAILED TABLE ---
            c.showPage()
            page_num = 2
            
            margin = 40
            total_width = w - 2 * margin
            ts_width = 130
            val_width = (total_width - ts_width) / len(selected_regs)
            
            # Adjust font size based on parameter count
            font_size = 8
            if len(selected_regs) > 8:
                font_size = 7
            if len(selected_regs) > 12:
                font_size = 6

            def draw_table_header(page):
                c.setFillColorRGB(0.06, 0.72, 0.51)
                c.rect(margin, h - 50, total_width, 22, fill=True, stroke=False)
                
                c.setFillColorRGB(0.4, 0.4, 0.4)
                c.setFont("Helvetica", 8)
                dev_name = dev.get('device_name') or dev['ip']
                c.drawString(margin, h - 25, f"THE LOGGER — HISTORIC DATA LOG ({dev_name})")
                c.drawRightString(w - margin, h - 25, f"Page {page}")
                
                c.setFillColorRGB(1, 1, 1)
                draw_cell(c, "TIMESTAMP", margin, h - 50, ts_width, 22, align="left", bold=True, font_size=font_size)
                for j, reg in enumerate(selected_regs):
                    name = addr_to_name.get(str(reg), f"REG {reg}")
                    draw_cell(c, name, margin + ts_width + j * val_width, h - 50, val_width, 22, align="right", bold=True, font_size=font_size)
                
                c.setStrokeColorRGB(0.8, 0.8, 0.8)
                c.setLineWidth(0.5)
                c.line(margin, h - 50, w - margin, h - 50)
                return h - 68

            y = draw_table_header(page_num)
            prec = int(self.dec_cb.currentText())
            
            for i, ts in enumerate(sorted(self.pivoted_data.keys())):
                if y < 45:
                    c.showPage()
                    page_num += 1
                    y = draw_table_header(page_num)
                
                if i % 2 == 0:
                    c.setFillColorRGB(1, 1, 1)
                else:
                    c.setFillColorRGB(0.96, 0.97, 0.98)
                c.rect(margin, y - 2, total_width, 16, fill=True, stroke=False)
                
                c.setStrokeColorRGB(0.9, 0.9, 0.9)
                c.setLineWidth(0.3)
                c.line(margin, y - 2, w - margin, y - 2)
                
                c.setFillColorRGB(0.2, 0.2, 0.2)
                draw_cell(c, ts, margin, y - 2, ts_width, 16, align="left", font_size=font_size)
                
                for j, reg in enumerate(selected_regs):
                    val = self.pivoted_data[ts].get(str(reg))
                    val_str = f"{val:.{prec}f}" if val is not None else "---"
                    c.setFillColorRGB(0.1, 0.1, 0.1)
                    draw_cell(c, val_str, margin + ts_width + j * val_width, y - 2, val_width, 16, align="right", font_size=font_size)
                
                y -= 16

            c.save()
            QMessageBox.information(self, "Exported", f"Saved to:\n{fn}")
            import webbrowser; webbrowser.open(fn)
        except Exception as ex:
            QMessageBox.critical(self, "Error", str(ex))
