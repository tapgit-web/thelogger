import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core import get_db
from app.models import DBUser
from app.utils.security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.username == req.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Hash password with sha256 to verify against database
    h = hashlib.sha256(req.password.encode()).hexdigest()
    if user.password_hash != h:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }
