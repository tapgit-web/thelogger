from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import io
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ReportLab Imports
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import bcrypt
import database
import models
import modbus_manager

# Initialize SQLite tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="THE LOGGER Web API", version="1.0.0")

# CORS Middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed Initial Administrator Account
def seed_admin():
    db = database.SessionLocal()
    try:
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin_user:
            hashed_pw = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.add(models.User(username="admin", hashed_password=hashed_pw, role="admin"))
            db.commit()
            print("Admin user seeded successfully.")
    finally:
        db.close()

seed_admin()

# Pydantic schemas for request validation
class UserLogin(BaseModel):
    username: str = ""
    password: str = ""

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"

class DeviceCreate(BaseModel):
    name: str
    connection_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    com_port: Optional[str] = None
    baudrate: Optional[int] = None
    parity: Optional[str] = None
    bytesize: Optional[int] = None
    stopbits: Optional[int] = None

class RegisterCreate(BaseModel):
    device_id: int
    name: str
    address: int
    register_type: str
    data_type: str
    multiplier: float = 1.0
    divisor: float = 1.0
    unit: str = ""
    limit_min: Optional[float] = None
    limit_max: Optional[float] = None

class EmailSettingsCreate(BaseModel):
    smtp_server: str
    smtp_port: int
    use_ssl: bool
    username: str
    password: str
    sender_email: str
    receiver_email: str

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Broadcast error to connection: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

# Background WebSocket Broadcast loop
import asyncio

async def websocket_telemetry_broadcast_task():
    while True:
        try:
            payload = {
                "type": "telemetry",
                "is_polling": modbus_manager.is_polling_active,
                "data": modbus_manager.live_readings
            }
            await manager.broadcast(payload)
        except Exception as e:
            print(f"Error in WS telemetry broadcast loop: {e}")
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    # Launch background task for broadcasting telemetry
    asyncio.create_task(websocket_telemetry_broadcast_task())

# =================== ENDPOINTS ===================

@app.post("/api/auth/login")
def login(payload: UserLogin, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not bcrypt.checkpw(payload.password.encode('utf-8'), user.hashed_password.encode('utf-8')):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    return {"username": user.username, "role": user.role}

@app.get("/api/users")
def get_users(db: Session = Depends(database.get_db)):
    users = db.query(models.User).all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in users]

@app.post("/api/users")
def create_user(payload: UserCreate, db: Session = Depends(database.get_db)):
    exists = db.query(models.User).filter(models.User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = bcrypt.hashpw(payload.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = models.User(username=payload.username, hashed_password=hashed, role=payload.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(database.get_db)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete default admin user")
    db.delete(u)
    db.commit()
    return {"status": "success"}

# DEVICE API Endpoints
@app.get("/api/devices")
def get_devices(db: Session = Depends(database.get_db)):
    return db.query(models.Device).all()

@app.post("/api/devices")
def create_device(payload: DeviceCreate, db: Session = Depends(database.get_db)):
    d = models.Device(**payload.dict())
    db.add(d)
    db.commit()
    db.refresh(d)
    return d

@app.put("/api/devices/{device_id}")
def update_device(device_id: int, payload: DeviceCreate, db: Session = Depends(database.get_db)):
    d = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    for k, v in payload.dict().items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return d

@app.delete("/api/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(database.get_db)):
    d = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(d)
    db.commit()
    return {"status": "success"}

@app.get("/api/devices/{device_id}/registers")
def get_registers(device_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.Register).filter(models.Register.device_id == device_id).all()

@app.post("/api/registers")
def create_register(payload: RegisterCreate, db: Session = Depends(database.get_db)):
    r = models.Register(**payload.dict())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@app.put("/api/registers/{register_id}")
def update_register(register_id: int, payload: RegisterCreate, db: Session = Depends(database.get_db)):
    r = db.query(models.Register).filter(models.Register.id == register_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Register mapping not found")
    for k, v in payload.dict().items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r

@app.delete("/api/registers/{register_id}")
def delete_register(register_id: int, db: Session = Depends(database.get_db)):
    r = db.query(models.Register).filter(models.Register.id == register_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Register mapping not found")
    db.delete(r)
    db.commit()
    return {"status": "success"}

# Email Alert Config Endpoint
@app.get("/api/settings/email")
def get_email_settings(db: Session = Depends(database.get_db)):
    s = db.query(models.SmtpSettings).first()
    if not s:
        return {}
    return s

@app.post("/api/settings/email")
def update_email_settings(payload: EmailSettingsCreate, db: Session = Depends(database.get_db)):
    s = db.query(models.SmtpSettings).first()
    if s:
        for k, v in payload.dict().items():
            setattr(s, k, v)
    else:
        s = models.SmtpSettings(**payload.dict())
        db.add(s)
    db.commit()
    db.refresh(s)
    return s

@app.post("/api/settings/test-email")
def send_test_email_endpoint(payload: EmailSettingsCreate):
    try:
        subject = "🧪 THE LOGGER - Test SMTP Alert Email"
        body = f"""
        This is a test notification from THE LOGGER Web Application.
        SMTP configurations are validated successfully!
        
        Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        msg = MIMEMultipart()
        msg['From'] = payload.sender_email
        msg['To'] = payload.receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        if payload.use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(payload.smtp_server, payload.smtp_port, context=context) as server:
                server.login(payload.username, payload.password)
                server.sendmail(payload.sender_email, payload.receiver_email, msg.as_string())
        else:
            with smtplib.SMTP(payload.smtp_server, payload.smtp_port) as server:
                server.login(payload.username, payload.password)
                server.sendmail(payload.sender_email, payload.receiver_email, msg.as_string())
        return {"status": "success", "message": "Test email successfully sent!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Telemetry Polling Control
@app.post("/api/polling/toggle")
def toggle_polling():
    if modbus_manager.is_polling_active:
        modbus_manager.stop_polling()
    else:
        modbus_manager.start_polling()
    return {"is_polling": modbus_manager.is_polling_active}

# Trends & PDF Report API Endpoints
@app.get("/api/trends/data")
def get_trend_data(register_id: int, start_date: str, end_date: str, db: Session = Depends(database.get_db)):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    readings = db.query(models.Reading).filter(
        models.Reading.register_id == register_id,
        models.Reading.timestamp >= start,
        models.Reading.timestamp < end
    ).order_by(models.Reading.timestamp.asc()).all()
    
    points = []
    vals = []
    for r in readings:
        points.append({
            "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "value": r.value
        })
        vals.append(r.value)
        
    stats = {
        "min": round(min(vals), 2) if vals else 0.0,
        "max": round(max(vals), 2) if vals else 0.0,
        "avg": round(sum(vals) / len(vals), 2) if vals else 0.0
    }
    
    return {"points": points, "stats": stats}

@app.get("/api/trends/export-pdf")
def export_pdf_report(register_id: int, start_date: str, end_date: str, db: Session = Depends(database.get_db)):
    register = db.query(models.Register).filter(models.Register.id == register_id).first()
    if not register:
        raise HTTPException(status_code=404, detail="Register mapping not found")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    readings = db.query(models.Reading).filter(
        models.Reading.register_id == register_id,
        models.Reading.timestamp >= start,
        models.Reading.timestamp < end
    ).order_by(models.Reading.timestamp.desc()).limit(100).all() # Limit to last 100 values to avoid document overflow

    # PDF Document Construction
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor('#10B981'),
        spaceAfter=12
    )
    
    story = []
    story.append(Paragraph("THE LOGGER - Historical Trend Report", title_style))
    story.append(Paragraph(f"Device: {register.device.name}", styles['Normal']))
    story.append(Paragraph(f"Register Channel: {register.name} (Address: {register.address})", styles['Normal']))
    story.append(Paragraph(f"Reporting Window: {start_date} to {end_date}", styles['Normal']))
    story.append(Spacer(1, 15))

    # Aggregated Summary statistics
    vals = [r.value for r in readings]
    min_val = min(vals) if vals else 0.0
    max_val = max(vals) if vals else 0.0
    avg_val = sum(vals) / len(vals) if vals else 0.0

    stats_data = [
        ["Stat", "Value", "Unit"],
        ["Minimum Value", f"{min_val:.2f}", register.unit],
        ["Maximum Value", f"{max_val:.2f}", register.unit],
        ["Average Value", f"{avg_val:.2f}", register.unit],
    ]
    
    stats_table = Table(stats_data, colWidths=[150, 100, 100])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0B0F17')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#9CA3AF')),
    ]))
    story.append(Paragraph("<b>Aggregated Telemetry Summary</b>", styles['Heading2']))
    story.append(Spacer(1, 8))
    story.append(stats_table)
    story.append(Spacer(1, 20))

    # Detail logs table
    table_data = [["Timestamp (UTC)", "Reading Value", "Unit", "Status"]]
    for r in readings:
        table_data.append([
            r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            f"{r.value:.2f}",
            register.unit,
            "NORMAL"
        ])
        
    log_table = Table(table_data, colWidths=[180, 120, 80, 100])
    log_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F2937')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))
    
    story.append(Paragraph(f"<b>Detailed Logs (Last {len(readings)} Data Points)</b>", styles['Heading2']))
    story.append(Spacer(1, 8))
    story.append(log_table)

    doc.build(story)
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment;filename=TrendReport_{register_id}.pdf"
    })

# WebSockets Telemetry Stream
@app.websocket("/api/ws/live")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Empty receive block to keep connection open and detect disconnection
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket endpoint exception: {e}")
    finally:
        manager.disconnect(websocket)
