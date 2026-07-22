import os
import csv
import io
from datetime import datetime
from typing import List, Dict, Any

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import letter, landscape

from app.core import LIVE_LOGS_PATH, MODBUS_OVERRIDE_HOST, MODBUS_OVERRIDE_PORT
from app.models import DBDevice, DBRegister

PALETTE = ["#10B981", "#28A745", "#4285F4", "#F29900", "#6F42C1", "#E83E8C", "#20C997", "#FD7E14"]

def parse_historical_data(device: DBDevice, register: DBRegister, start_dt: datetime, end_dt: datetime) -> List[Dict[str, Any]]:
    host = MODBUS_OVERRIDE_HOST if (device.connection_type == "TCP" and MODBUS_OVERRIDE_HOST) else device.host
    port_or_baud = MODBUS_OVERRIDE_PORT if (device.connection_type == "TCP" and MODBUS_OVERRIDE_PORT) else (device.port or device.baudrate or 0)
    slave_id = getattr(device, "slave_id", 1)
    
    clean_ip = (host or device.com_port or "unknown").replace('.', '_').replace(':', '_').replace('/', '_').replace('\\', '_')
    prefix = f"{clean_ip}_{port_or_baud}_s{slave_id}"
    live_dir = LIVE_LOGS_PATH
    
    all_files = sorted([
        os.path.join(live_dir, f)
        for f in os.listdir(live_dir)
        if f.startswith(prefix) and f.endswith(".csv")
    ]) if os.path.exists(live_dir) else []
    
    points = []
    reg_addr_str = str(register.address)
    
    for fname in all_files:
        try:
            with open(fname, "r") as f:
                reader = csv.reader(f)
                next(reader, None) # skip header
                for row in reader:
                    if len(row) > 5 and str(row[4]) == reg_addr_str:
                        try:
                            row_dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                            if start_dt <= row_dt <= end_dt:
                                points.append({
                                    "timestamp": row[0],
                                    "value": float(row[5])
                                })
                        except Exception:
                            pass
        except Exception:
            continue
            
    # Sort points by timestamp
    points.sort(key=lambda p: p["timestamp"])
    return points

def render_report_pdf(device: DBDevice, registers_data: List[Dict[str, Any]], start_dt: datetime, end_dt: datetime) -> bytes:
    buffer = io.BytesIO()
    w, h = letter # 612 x 792 (Portrait Letter)
    c = rl_canvas.Canvas(buffer, pagesize=letter)
    
    margin_x = 35
    total_w = w - 2 * margin_x # 542
    
    # -------------------------------------------------------------
    # 1. TOP LOGO BANNER & HEADER METADATA
    # -------------------------------------------------------------
    # Primary M-OBSERVER Logo Title Banner
    c.setFillColorRGB(0.94, 0.27, 0.27) # Theme Crimson Red
    c.rect(margin_x, h - 60, total_w, 32, fill=True, stroke=False)
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_x + 12, h - 42, "M-OBSERVER")
    
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w - margin_x - 12, h - 40, "HISTORIC TREND REPORT")
    
    # Metadata Details Below Logo Banner
    host = MODBUS_OVERRIDE_HOST if (device.connection_type == "TCP" and MODBUS_OVERRIDE_HOST) else device.host
    dev_str = f"DEVICE: {device.name} ({host or device.com_port or 'N/A'})"
    exp_str = f"EXPORTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    range_str = f"RANGE: {start_dt.strftime('%Y-%m-%d %H:%M')} TO {end_dt.strftime('%Y-%m-%d %H:%M')}"
    
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(margin_x, h - 75, f"{dev_str} | {exp_str}")
    c.drawString(margin_x, h - 87, range_str)
    
    # Divider line under metadata
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(1.0)
    c.line(margin_x, h - 94, w - margin_x, h - 94)
    
    # -------------------------------------------------------------
    # 2. GRAPH CONTAINER BOX & PLOT CANVAS (PORTRAIT MODE)
    # -------------------------------------------------------------
    box_x = margin_x
    box_y = 475
    box_w = total_w
    box_h = 210
    
    # Light pinkish/soft background tint
    c.setFillColorRGB(0.99, 0.955, 0.955)
    c.rect(box_x, box_y, box_w, box_h, fill=True, stroke=False)
    
    # Plot canvas dimensions inside the box
    x_min = box_x + 65
    x_max = box_x + 375
    y_min = box_y + 20
    y_max = box_y + 185
    W_plot = x_max - x_min
    H_plot = y_max - y_min
    
    # Collect points, timestamps, and values
    all_timestamps_set = set()
    all_values = []
    
    for reg_info in registers_data:
        for p in reg_info.get("points", []):
            all_timestamps_set.add(p["timestamp"])
            all_values.append(p["value"])
            
    sorted_timestamps = sorted(list(all_timestamps_set))
    t_count = len(sorted_timestamps)
    
    if not all_values:
        min_y, max_y = 0.0, 100.0
    else:
        min_y = min(all_values)
        max_y = max(all_values)
        
    if min_y == max_y:
        min_y -= 10
        max_y += 10
    else:
        padding = (max_y - min_y) * 0.1
        min_y -= padding
        max_y += padding
        
    # Draw Y-Axis labels & Grid lines
    c.setStrokeColorRGB(0.88, 0.88, 0.88)
    c.setLineWidth(0.5)
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    
    for i in range(6):
        y_val = min_y + i * (max_y - min_y) / 5
        sy = y_min + (i * H_plot / 5)
        c.line(x_min, sy, x_max, sy)
        c.drawRightString(x_min - 8, sy - 2.5, f"{y_val:.3f}")
        
    # Draw X-Axis labels & Grid lines
    if t_count > 1:
        for i in range(5):
            idx = int(i * (t_count - 1) / 4)
            time_raw = sorted_timestamps[idx]
            sx = x_min + (i * W_plot / 4)
            c.line(sx, y_min, sx, y_max)
            try:
                time_str = time_raw.split(" ")[1]
            except Exception:
                time_str = time_raw
            c.drawCentredString(sx, y_min - 12, time_str)
    else:
        c.line(x_min + W_plot/2, y_min, x_min + W_plot/2, y_max)
        c.drawCentredString(x_min + W_plot/2, y_min - 12, "00:00:00")
        
    # Plot data curves
    for idx_reg, reg_info in enumerate(registers_data):
        pts = reg_info.get("points", [])
        if not pts:
            continue
            
        color_hex = PALETTE[idx_reg % len(PALETTE)]
        r_col = int(color_hex[1:3], 16) / 255.0
        g_col = int(color_hex[3:5], 16) / 255.0
        b_col = int(color_hex[5:7], 16) / 255.0
        
        c.setStrokeColorRGB(r_col, g_col, b_col)
        c.setLineWidth(1.8)
        path = c.beginPath()
        
        for idx_p, pt in enumerate(pts):
            if t_count > 1:
                try:
                    t_idx = sorted_timestamps.index(pt["timestamp"])
                    sx = x_min + (t_idx / (t_count - 1)) * W_plot
                except ValueError:
                    sx = x_min + (idx_p / max(len(pts) - 1, 1)) * W_plot
            else:
                sx = x_min + W_plot / 2
                
            sy = y_min + ((pt["value"] - min_y) / (max_y - min_y)) * H_plot
            if idx_p == 0:
                path.moveTo(sx, sy)
            else:
                path.lineTo(sx, sy)
        c.drawPath(path, stroke=True, fill=False)
        
    # Limit lines (dashed)
    c.setLineWidth(1.0)
    for idx_reg, reg_info in enumerate(registers_data):
        reg = reg_info["register"]
        lo_val = reg.limit_min
        hi_val = reg.limit_max
        
        if lo_val is not None:
            c.setStrokeColorRGB(0.85, 0.25, 0.25)
            c.setDash(3, 2)
            sy = y_min + ((lo_val - min_y) / (max_y - min_y)) * H_plot
            if y_min <= sy <= y_max:
                c.line(x_min, sy, x_max, sy)
                c.setFont("Helvetica", 7)
                c.setFillColorRGB(0.35, 0.35, 0.35)
                c.drawString(x_max + 6, sy - 2.5, f"LOW: {lo_val}")
                
        if hi_val is not None:
            c.setStrokeColorRGB(0.85, 0.25, 0.25)
            c.setDash(3, 2)
            sy = y_min + ((hi_val - min_y) / (max_y - min_y)) * H_plot
            if y_min <= sy <= y_max:
                c.line(x_min, sy, x_max, sy)
                c.setFont("Helvetica", 7)
                c.setFillColorRGB(0.35, 0.35, 0.35)
                c.drawString(x_max + 6, sy - 2.5, f"UPPER: {hi_val}")
                
    c.setDash()
    
    # Legend Stacked Vertically on the Right Side of Graph Box
    leg_x = box_x + 390
    leg_y = y_max - 5
    for idx_reg, reg_info in enumerate(registers_data):
        reg = reg_info["register"]
        color_hex = PALETTE[idx_reg % len(PALETTE)]
        r_col = int(color_hex[1:3], 16) / 255.0
        g_col = int(color_hex[3:5], 16) / 255.0
        b_col = int(color_hex[5:7], 16) / 255.0
        
        # Color Box
        c.setFillColorRGB(r_col, g_col, b_col)
        c.rect(leg_x, leg_y - 1, 9, 9, fill=True, stroke=False)
        
        # Parameter Name
        c.setFont("Helvetica-Bold", 8)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        param_name = reg.name.upper()
        if len(param_name) > 18:
            param_name = param_name[:16] + "..."
        c.drawString(leg_x + 14, leg_y, param_name)
        
        leg_y -= 16
        if leg_y < box_y + 10:
            break
            
    # Inner Plot Frame Box
    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    c.setLineWidth(1.0)
    c.rect(x_min, y_min, W_plot, H_plot, fill=False, stroke=True)
    
    # -------------------------------------------------------------
    # 3. HISTORICAL DATA LOG TABLE (RED BANNER DESIGN THEME)
    # -------------------------------------------------------------
    c.showPage()
    page_num = 2
    margin = margin_x
    
    num_regs = len(registers_data)
    ts_col_w = 160
    reg_col_w = (total_w - ts_col_w) / max(num_regs, 1)
    
    time_val_map = {}
    for reg_info in registers_data:
        r_id = reg_info["register"].id
        for p in reg_info.get("points", []):
            ts = p["timestamp"]
            if ts not in time_val_map:
                time_val_map[ts] = {}
            time_val_map[ts][r_id] = p["value"]
            
    def draw_table_header_red_theme(p_num):
        top_y = h - 30
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.setFont("Helvetica", 8)
        reg_title = ", ".join([r["register"].name for r in registers_data])
        if len(reg_title) > 55:
            reg_title = reg_title[:52] + "..."
        c.drawString(margin, top_y, f"M-OBSERVER — DATA LOG — {reg_title} ({device.name})")
        c.drawRightString(w - margin, top_y, f"Page {p_num}")
        
        banner_y = top_y - 28
        c.setFillColorRGB(0.94, 0.27, 0.27) # Red Banner
        c.rect(margin, banner_y, total_w, 20, fill=True, stroke=False)
        
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin + 5, banner_y + 6, "TIMESTAMP")
        
        for idx_r, reg_info in enumerate(registers_data):
            reg = reg_info["register"]
            if num_regs == 1:
                c.drawRightString(w - margin - 5, banner_y + 6, f"{reg.name.upper()} ({reg.unit or 'N/A'})")
            else:
                col_x_right = margin + ts_col_w + (idx_r + 1) * reg_col_w - 5
                c.drawRightString(col_x_right, banner_y + 6, f"{reg.name[:16].upper()} ({reg.unit or ''})")
                
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.setLineWidth(0.5)
        c.line(margin, banner_y, w - margin, banner_y)
        return banner_y - 18

    y_row = draw_table_header_red_theme(page_num)
    
    # Print Rows with Alternating Background Tint
    for row_idx, ts in enumerate(sorted_timestamps):
        if y_row < 45:
            c.showPage()
            page_num += 1
            y_row = draw_table_header_red_theme(page_num)
            
        if row_idx % 2 == 0:
            c.setFillColorRGB(1, 1, 1)
        else:
            c.setFillColorRGB(0.96, 0.97, 0.98)
            
        c.rect(margin, y_row - 2, total_w, 16, fill=True, stroke=False)
        
        c.setStrokeColorRGB(0.9, 0.9, 0.9)
        c.setLineWidth(0.3)
        c.line(margin, y_row - 2, w - margin, y_row - 2)
        
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.setFont("Helvetica", 8)
        c.drawString(margin + 5, y_row + 2, ts)
        
        reg_vals = time_val_map.get(ts, {})
        for idx_r, reg_info in enumerate(registers_data):
            r_id = reg_info["register"].id
            val = reg_vals.get(r_id)
            val_str = f"{val:.3f}" if val is not None else "-"
            if num_regs == 1:
                c.drawRightString(w - margin - 5, y_row + 2, val_str)
            else:
                col_x_right = margin + ts_col_w + (idx_r + 1) * reg_col_w - 5
                c.drawRightString(col_x_right, y_row + 2, val_str)
                
        y_row -= 16
        
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def generate_pdf_report(device: DBDevice, register: DBRegister, points: List[Dict[str, Any]], start_dt: datetime, end_dt: datetime) -> bytes:
    return render_report_pdf(device, [{"register": register, "points": points}], start_dt, end_dt)

def generate_multiple_pdf_report(device: DBDevice, registers_data: List[Dict[str, Any]], start_dt: datetime, end_dt: datetime) -> bytes:
    return render_report_pdf(device, registers_data, start_dt, end_dt)
