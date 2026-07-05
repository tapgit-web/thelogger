import sys
import os
import hashlib

# Ensure backend root directory is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core import SessionLocal
from app.models import DBUser

def seed_user(username, password, role="admin"):
    db = SessionLocal()
    try:
        existing = db.query(DBUser).filter(DBUser.username == username).first()
        if existing:
            # Update password
            existing.password_hash = hashlib.sha256(password.encode()).hexdigest()
            existing.role = role
            db.commit()
            print(f"User '{username}' already exists. Password and role updated successfully!")
        else:
            # Create user
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            new_user = DBUser(username=username, password_hash=pw_hash, role=role)
            db.add(new_user)
            db.commit()
            print(f"User '{username}' seeded successfully with role '{role}'!")
    except Exception as e:
        print(f"Error seeding user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python seed_user.py <username> <password> [role]")
        print("Example: python seed_user.py manager pass123 user")
    else:
        uname = sys.argv[1]
        pwd = sys.argv[2]
        rle = sys.argv[3] if len(sys.argv) > 3 else "admin"
        seed_user(uname, pwd, rle)
