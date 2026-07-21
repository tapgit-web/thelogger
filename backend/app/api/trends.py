from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional

from app.core import get_db
from app.models import DBDevice, DBRegister
from app.services.pdf_report import parse_historical_data, generate_pdf_report, generate_multiple_pdf_report
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/trends", tags=["trends"])

def parse_date(date_str: str, is_end_date: bool = False) -> datetime:
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if fmt == "%Y-%m-%d" and is_end_date:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            continue
    raise ValueError(f"Time data '{date_str}' does not match any allowed formats.")

@router.get("/data")
def get_trends_data(
    register_id: Optional[int] = None,
    register_ids: Optional[str] = None,
    start_date: str = Query(...), # Format: 'YYYY-MM-DDTHH:MM' or 'YYYY-MM-DD HH:MM:SS'
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if register_id is not None and not register_ids:
        reg = db.query(DBRegister).filter(DBRegister.id == register_id).first()
        if not reg:
            raise HTTPException(status_code=404, detail="Register not found")
        dev = db.query(DBDevice).filter(DBDevice.id == reg.device_id).first()
        
        try:
            start_dt = parse_date(start_date, is_end_date=False)
            end_dt = parse_date(end_date, is_end_date=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
            
        points = parse_historical_data(dev, reg, start_dt, end_dt)
        vals = [p["value"] for p in points]
        stats = {
            "min": min(vals) if vals else 0.0,
            "max": max(vals) if vals else 0.0,
            "avg": sum(vals) / len(vals) if vals else 0.0
        }
        return {
            "points": [{"timestamp": p["timestamp"], "value": p["value"]} for p in points],
            "stats": stats
        }

    ids = []
    if register_ids:
        ids = [int(x) for x in register_ids.split(",") if x.strip()]
    else:
        raise HTTPException(status_code=400, detail="Missing register_id or register_ids")
        
    results = {}
    for r_id in ids:
        reg = db.query(DBRegister).filter(DBRegister.id == r_id).first()
        if not reg:
            continue
        dev = db.query(DBDevice).filter(DBDevice.id == reg.device_id).first()
        
        try:
            start_dt = parse_date(start_date, is_end_date=False)
            end_dt = parse_date(end_date, is_end_date=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
            
        points = parse_historical_data(dev, reg, start_dt, end_dt)
        vals = [p["value"] for p in points]
        stats = {
            "min": min(vals) if vals else 0.0,
            "max": max(vals) if vals else 0.0,
            "avg": sum(vals) / len(vals) if vals else 0.0
        }
        results[r_id] = {
            "points": [{"timestamp": p["timestamp"], "value": p["value"]} for p in points],
            "stats": stats
        }
        
    return results

@router.get("/export-pdf")
def export_trends_pdf(
    register_id: Optional[int] = None,
    register_ids: Optional[str] = None,
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    ids = []
    if register_ids:
        ids = [int(x) for x in register_ids.split(",") if x.strip()]
    elif register_id is not None:
        ids = [register_id]
    else:
        raise HTTPException(status_code=400, detail="Missing register_id or register_ids")
        
    if not ids:
        raise HTTPException(status_code=400, detail="No valid register IDs provided")
        
    try:
        start_dt = parse_date(start_date, is_end_date=False)
        end_dt = parse_date(end_date, is_end_date=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
        
    registers_data = []
    primary_device = None
    
    for r_id in ids:
        reg = db.query(DBRegister).filter(DBRegister.id == r_id).first()
        if not reg:
            continue
        dev = db.query(DBDevice).filter(DBDevice.id == reg.device_id).first()
        if not primary_device:
            primary_device = dev
        points = parse_historical_data(dev, reg, start_dt, end_dt)
        registers_data.append({
            "register": reg,
            "points": points
        })
        
    if not registers_data or not primary_device:
        raise HTTPException(status_code=404, detail="No registers or device found")
        
    if len(registers_data) == 1:
        pdf_bytes = generate_pdf_report(primary_device, registers_data[0]["register"], registers_data[0]["points"], start_dt, end_dt)
        filename = f"TrendReport_{registers_data[0]['register'].name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    else:
        pdf_bytes = generate_multiple_pdf_report(primary_device, registers_data, start_dt, end_dt)
        filename = f"Combined_TrendReport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
