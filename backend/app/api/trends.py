from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core import get_db
from app.models import DBDevice, DBRegister
from app.services.pdf_report import parse_historical_data, generate_pdf_report
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/trends", tags=["trends"])

@router.get("/data")
def get_trends_data(
    register_id: int,
    start_date: str = Query(...), # Format: 'YYYY-MM-DDTHH:MM' or 'YYYY-MM-DD HH:MM:SS'
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    reg = db.query(DBRegister).filter(DBRegister.id == register_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Register not found")
    
    dev = db.query(DBDevice).filter(DBDevice.id == reg.device_id).first()
    
    # Parse datetimes
    try:
        # Standard Next.js Datetime-Local format: 'YYYY-MM-DDTHH:MM'
        if 'T' in start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        else:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            
        if 'T' in end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
        else:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
        
    points = parse_historical_data(dev, reg, start_dt, end_dt)
    
    # Calculate stats
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

@router.get("/export-pdf")
def export_trends_pdf(
    register_id: int,
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    reg = db.query(DBRegister).filter(DBRegister.id == register_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Register not found")
        
    dev = db.query(DBDevice).filter(DBDevice.id == reg.device_id).first()
    
    try:
        if 'T' in start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        else:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            
        if 'T' in end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%dT%H:%M")
        else:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
        
    points = parse_historical_data(dev, reg, start_dt, end_dt)
    pdf_bytes = generate_pdf_report(dev, reg, points, start_dt, end_dt)
    
    filename = f"TrendReport_{reg.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
