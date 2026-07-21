from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core import get_db
from app.models import DBEmailSettings
from app.utils import send_email
from app.utils.security import get_current_user, get_admin_user

router = APIRouter(prefix="/api/settings", tags=["settings"])

class EmailSettingsUpdate(BaseModel):
    smtp_server: str
    smtp_port: int
    use_ssl: bool
    username: str
    password: str
    sender_email: str
    receiver_email: str

@router.get("/email")
def get_email_settings(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(DBEmailSettings).filter_by(id=1).first()

@router.post("/email")
def update_email_settings(req: EmailSettingsUpdate, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    settings = db.query(DBEmailSettings).filter_by(id=1).first()
    if not settings:
        settings = DBEmailSettings(id=1)
        db.add(settings)
        
    settings.smtp_server = req.smtp_server
    settings.smtp_port = req.smtp_port
    settings.use_ssl = req.use_ssl
    settings.username = req.username
    settings.password = req.password
    settings.sender_email = req.sender_email
    settings.receiver_email = req.receiver_email
    
    db.commit()
    db.refresh(settings)
    return settings

@router.post("/test-email")
def test_email(req: EmailSettingsUpdate, current_user = Depends(get_admin_user)):
    settings = DBEmailSettings(
        smtp_server=req.smtp_server,
        smtp_port=req.smtp_port,
        use_ssl=req.use_ssl,
        username=req.username,
        password=req.password,
        sender_email=req.sender_email,
        receiver_email=req.receiver_email
    )
    ok = send_email(
        subject="M-OBSERVER - SMTP Configuration Test Alert",
        body="Congratulations! Your SMTP email alerts settings are correctly configured.",
        settings=settings
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to send test email. Check server or credentials.")
    return {"status": "success", "message": "Test email sent successfully"}
