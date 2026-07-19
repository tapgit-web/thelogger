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

def generate_pdf_report(device: DBDevice, register: DBRegister, points: List[Dict[str, Any]], start_dt: datetime, end_dt: datetime) -> bytes:
    buffer = io.BytesIO()
    
    # Landscape Letter
    w, h = landscape(letter)
    c = rl_canvas.Canvas(buffer, pagesize=landscape(letter))
    
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
    c.drawString(60, h - 118, "Parameter:")
    c.drawString(60, h - 136, "Date Range:")
    
    host = MODBUS_OVERRIDE_HOST if (device.connection_type == "TCP" and MODBUS_OVERRIDE_HOST) else device.host
    c.setFont("Helvetica", 9)
    c.drawString(140, h - 100, f"{device.name} ({host or device.com_port})")
    c.drawString(140, h - 118, f"{register.name} (Addr: {register.address}, Unit: {register.unit or 'N/A'})")
    c.drawString(140, h - 136, f"{start_dt.strftime('%Y-%m-%d %H:%M:%S')}  to  {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(500, h - 100, "Total Records:")
    c.drawString(500, h - 118, "Exported at:")
    
    c.setFont("Helvetica", 9)
    c.drawString(600, h - 100, f"{len(points)}")
    c.drawString(600, h - 118, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Graph Area
    x_min = 70
    x_max = w - 40
    y_min = 60
    y_max = h - 180
    W_plot = x_max - x_min
    H_plot = y_max - y_min
    
    c.setFillColorRGB(0.97, 0.97, 0.98)
    c.rect(x_min, y_min, W_plot, H_plot, fill=True, stroke=True)
    
    # Calculate limits
    vals = [p["value"] for p in points] if points else [0.0, 100.0]
    
    lo_val = register.limit_min
    hi_val = register.limit_max
    
    if lo_val is not None:
        vals.append(lo_val)
    if hi_val is not None:
        vals.append(hi_val)
        
    min_y = min(vals)
    max_y = max(vals)
    if min_y == max_y:
        min_y -= 10
        max_y += 10
    else:
        padding = (max_y - min_y) * 0.1
        min_y -= padding
        max_y += padding
        
    # Y-Axis Grid & Labels
    c.setStrokeColorRGB(0.85, 0.85, 0.85)
    c.setLineWidth(0.5)
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    for i in range(5):
        y_val = min_y + i * (max_y - min_y) / 4
        sy = y_min + (i * H_plot / 4)
        c.line(x_min, sy, x_max, sy)
        c.drawRightString(x_min - 8, sy - 2.5, f"{y_val:.3f}")
        
    # X-Axis Grid & Labels
    t_count = len(points)
    if t_count > 1:
        for i in range(5):
            idx = int(i * (t_count - 1) / 4)
            pt = points[idx]
            sx = x_min + (i * W_plot / 4)
            c.line(sx, y_min, sx, y_max)
            try:
                time_str = pt["timestamp"].split(" ")[1] # HH:MM:SS
            except Exception:
                time_str = pt["timestamp"]
            c.drawCentredString(sx, y_min - 12, time_str)
    else:
        c.line(x_min + W_plot/2, y_min, x_min + W_plot/2, y_max)
        c.drawCentredString(x_min + W_plot/2, y_min - 12, "00:00:00")
        
    # Draw curves
    if points:
        c.setStrokeColorRGB(0.06, 0.72, 0.51) # Emerald color
        c.setLineWidth(1.5)
        path = c.beginPath()
        for idx, pt in enumerate(points):
            sx = x_min + (idx / max(t_count - 1, 1)) * W_plot
            sy = y_min + ((pt["value"] - min_y) / (max_y - min_y)) * H_plot
            if idx == 0:
                path.moveTo(sx, sy)
            else:
                path.lineTo(sx, sy)
        c.drawPath(path, stroke=True, fill=False)
        
    # Limit lines
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
            c.drawString(x_min + 10, sy + 3, f"High Limit: {hi_val}")
            
    c.setDash() # clear dash
    
    # Legend
    leg_x = x_min + 10
    leg_y = y_max + 8
    c.setFont("Helvetica-Bold", 7)
    c.setStrokeColorRGB(0.06, 0.72, 0.51)
    c.setLineWidth(2.5)
    c.line(leg_x, leg_y + 2.5, leg_x + 15, leg_y + 2.5)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(leg_x + 20, leg_y, f"{register.name} ({register.unit})")
    
    # Chart border
    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    c.setLineWidth(1.0)
    c.rect(x_min, y_min, W_plot, H_plot, fill=False, stroke=True)
    
    # --- PAGE 2+: DATA TABLE ---
    c.showPage()
    page_num = 2
    margin = 40
    total_width = w - 2 * margin
    ts_width = 200
    val_width = total_width - ts_width
    
    def draw_table_header(page):
        c.setFillColorRGB(0.06, 0.72, 0.51)
        c.rect(margin, h - 50, total_width, 22, fill=True, stroke=False)
        
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.setFont("Helvetica", 8)
        c.drawString(margin, h - 25, f"THE LOGGER — HISTORIC DATA LOG ({device.name})")
        c.drawRightString(w - margin, h - 25, f"Page {page}")
        
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin + 5, h - 45, "TIMESTAMP")
        c.drawRightString(w - margin - 5, h - 45, f"{register.name} ({register.unit or 'N/A'})")
        
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.setLineWidth(0.5)
        c.line(margin, h - 50, w - margin, h - 50)
        return h - 68

    y = draw_table_header(page_num)
    
    for i, pt in enumerate(points):
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
        c.setFont("Helvetica", 8)
        c.drawString(margin + 5, y + 2, pt["timestamp"])
        c.drawRightString(w - margin - 5, y + 2, f"{pt['value']:.3f}")
        
        y -= 16
        
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
