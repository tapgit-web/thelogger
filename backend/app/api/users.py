import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core import get_db
from app.models import DBUser
from app.utils.security import get_admin_user

router = APIRouter(prefix="/api/users", tags=["users"])

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

@router.get("")
def get_users(db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    users = db.query(DBUser).all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in users]

@router.post("")
def create_user(req: UserCreate, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    existing = db.query(DBUser).filter(DBUser.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    h = hashlib.sha256(req.password.encode()).hexdigest()
    user = DBUser(username=req.username, password_hash=h, role=req.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "role": user.role}

@router.delete("/{id}")
def delete_user(id: int, db: Session = Depends(get_db), current_user = Depends(get_admin_user)):
    user = db.query(DBUser).filter(DBUser.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete default admin user")
    db.delete(user)
    db.commit()
    return {"status": "success"}
