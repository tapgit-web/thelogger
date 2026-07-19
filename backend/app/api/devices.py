import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core import get_db
from app.models import DBDevice, DBRegister
from app.services.modbus_worker import is_polling, start_polling, stop_polling
from app.utils.security import get_current_user, get_admin_user

router = APIRouter(tags=["devices"])

class DeviceCreate(BaseModel):
    name: str
    connection_type: str  # "TCP" or "RTU"
    # TCP fields
    host: Optional[str] = None
    port: Optional[int] = None
    # RTU fields
    com_port: Optional[str] = None
    baudrate: Optional[int] = None
    parity: Optional[str] = None
    bytesize: Optional[int] = None
    stopbits: Optional[int] = None
    slave_id: int = 1

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

@router.get("/api/devices")
def get_devices(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(DBDevice).all()

@router.post("/api/devices")
def create_device(req: DeviceCreate, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    existing = db.query(DBDevice).filter(DBDevice.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device name already exists")
        
    dev = DBDevice(
        name=req.name,
        connection_type=req.connection_type,
        host=req.host,
        port=req.port,
        com_port=req.com_port,
        baudrate=req.baudrate,
        parity=req.parity,
        bytesize=req.bytesize,
        stopbits=req.stopbits,
        slave_id=req.slave_id
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    
    if is_polling:
        stop_polling()
        start_polling(asyncio.get_event_loop())

    return dev

@router.put("/api/devices/{id}")
def update_device(id: int, req: DeviceCreate, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    dev = db.query(DBDevice).filter(DBDevice.id == id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
        
    dev.name = req.name
    dev.connection_type = req.connection_type
    dev.host = req.host
    dev.port = req.port
    dev.com_port = req.com_port
    dev.baudrate = req.baudrate
    dev.parity = req.parity
    dev.bytesize = req.bytesize
    dev.stopbits = req.stopbits
    dev.slave_id = req.slave_id
    
    db.commit()
    db.refresh(dev)
    
    if is_polling:
        stop_polling()
        start_polling(asyncio.get_event_loop())

    return dev

@router.delete("/api/devices/{id}")
def delete_device(id: int, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    dev = db.query(DBDevice).filter(DBDevice.id == id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
        
    db.delete(dev)
    db.commit()
    
    if is_polling:
        stop_polling()
        start_polling(asyncio.get_event_loop())

    return {"status": "success"}

@router.get("/api/devices/{deviceId}/registers")
def get_device_registers(deviceId: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(DBRegister).filter(DBRegister.device_id == deviceId).all()

# --- Register Mapping ---
@router.post("/api/registers")
def create_register(req: RegisterCreate, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    reg = DBRegister(
        device_id=req.device_id,
        name=req.name,
        address=req.address,
        register_type=req.register_type,
        data_type=req.data_type,
        multiplier=req.multiplier,
        divisor=req.divisor,
        unit=req.unit,
        limit_min=req.limit_min,
        limit_max=req.limit_max
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    
    if is_polling:
        stop_polling()
        start_polling(asyncio.get_event_loop())

    return reg

@router.put("/api/registers/{id}")
def update_register(id: int, req: RegisterCreate, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    reg = db.query(DBRegister).filter(DBRegister.id == id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Register not found")
        
    reg.name = req.name
    reg.address = req.address
    reg.register_type = req.register_type
    reg.data_type = req.data_type
    reg.multiplier = req.multiplier
    reg.divisor = req.divisor
    reg.unit = req.unit
    reg.limit_min = req.limit_min
    reg.limit_max = req.limit_max
    
    db.commit()
    db.refresh(reg)
    
    if is_polling:
        stop_polling()
        start_polling(asyncio.get_event_loop())

    return reg

@router.delete("/api/registers/{id}")
def delete_register(id: int, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    reg = db.query(DBRegister).filter(DBRegister.id == id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Register not found")
        
    db.delete(reg)
    db.commit()
    
    if is_polling:
        stop_polling()
        start_polling(asyncio.get_event_loop())

    return {"status": "success"}
