import os
import json
import hashlib
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import (
    DATABASE_URL, DATA_PATH, LIVE_LOGS_PATH,
    LEGACY_AUTH_DECRYPT_KEY, LEGACY_DEVICE_DECRYPT_KEY,
    DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
)
from app.models.db_models import Base, DBUser, DBDevice, DBRegister, DBEmailSettings
from app.utils.security import decrypt_config

if DATABASE_URL.startswith("sqlite"):
    print("Database: Connecting to SQLite local database.")
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    db_type = DATABASE_URL.split("://")[0].split("+")[0].upper()
    print(f"Database: Connecting to {db_type} database.")
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def run_migrations():
    init_db()
    db = SessionLocal()
    try:
        # Check if database has users. If not, try migrating users
        if db.query(DBUser).count() == 0:
            desktop_users_path = "/home/vicky/praveen-projects/python-desktop-application/logger_app/config/users.json"
            users_migrated = False
            if os.path.exists(desktop_users_path):
                try:
                    with open(desktop_users_path, "r") as f:
                        content = f.read().strip()
                    # Decrypt users.json using legacy key
                    dec = decrypt_config(content, LEGACY_AUTH_DECRYPT_KEY)
                    if dec:
                        users_data = json.loads(dec)
                        for uname, uinfo in users_data.items():
                            role = "admin" if uinfo.get("is_admin") else "user"
                            pw_hash = uinfo.get("password")
                            db.add(DBUser(username=uname, password_hash=pw_hash, role=role))
                        db.commit()
                        users_migrated = True
                        print("Migrated users configuration from desktop app.")
                except Exception as e:
                    print(f"Error migrating users.json: {e}")

            if not users_migrated:
                # Add default admin
                admin_hash = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
                db.add(DBUser(username=DEFAULT_ADMIN_USERNAME, password_hash=admin_hash, role="admin"))
                db.commit()
                print(f"Created default admin user: {DEFAULT_ADMIN_USERNAME}")

        # Migrate email settings
        if db.query(DBEmailSettings).count() == 0:
            desktop_email_path = "/home/vicky/praveen-projects/python-desktop-application/logger_app/config/email_settings.json"
            settings_migrated = False
            if os.path.exists(desktop_email_path):
                try:
                    with open(desktop_email_path, "r") as f:
                        content = f.read().strip()
                    # Decrypt email_settings.json using legacy key
                    dec = decrypt_config(content, LEGACY_AUTH_DECRYPT_KEY)
                    if dec:
                        email_data = json.loads(dec)
                        db.add(DBEmailSettings(
                            id=1,
                            smtp_server=email_data.get("smtp_server", "smtp.gmail.com"),
                            smtp_port=int(email_data.get("smtp_port", 587)),
                            use_ssl=(str(email_data.get("smtp_port")) == "465"),
                            username=email_data.get("sender_email", ""),
                            password=email_data.get("sender_password", ""),
                            sender_email=email_data.get("sender_email", ""),
                            receiver_email=email_data.get("recipient_email", "")
                        ))
                        db.commit()
                        settings_migrated = True
                        print("Migrated email settings configuration from desktop app.")
                except Exception as e:
                    print(f"Error migrating email_settings.json: {e}")
            
            if not settings_migrated:
                db.add(DBEmailSettings(id=1))
                db.commit()

        # Migrate devices and registers
        if db.query(DBDevice).count() == 0:
            desktop_devices_path = "/home/vicky/praveen-projects/python-desktop-application/logger_app/config/devices.json"
            if os.path.exists(desktop_devices_path):
                try:
                    with open(desktop_devices_path, "r") as f:
                        content = f.read().strip()
                    # Decrypt devices.json using legacy key
                    dec = decrypt_config(content, LEGACY_DEVICE_DECRYPT_KEY)
                    if dec:
                        devices_list = json.loads(dec)
                        for d in devices_list:
                            conn_type = d.get("conn_type", "TCP").upper()
                            dev = DBDevice(
                                name=d.get("device_name", "Device"),
                                connection_type=conn_type,
                                host=d.get("ip") if conn_type == "TCP" else None,
                                port=int(d.get("port", 502)) if conn_type == "TCP" else None,
                                com_port=d.get("com_port") if conn_type == "RTU" else None,
                                baudrate=int(d.get("baudrate", 9600)) if conn_type == "RTU" else None,
                                parity=d.get("parity", "N") if conn_type == "RTU" else None,
                                bytesize=int(d.get("bytesize", 8)) if conn_type == "RTU" else None,
                                stopbits=int(d.get("stopbits", 1)) if conn_type == "RTU" else None
                            )
                            db.add(dev)
                            db.flush()  # gets dev.id

                            # Migrate registers of this device
                            registers = d.get("registers", [])
                            names = d.get("names", {})
                            types = d.get("types", {})
                            modes = d.get("modes", {})
                            factors = d.get("factors", {})
                            ops = d.get("ops", {})
                            units = d.get("units", {})

                            for reg_addr in registers:
                                addr_str = str(reg_addr)
                                reg_name = names.get(addr_str, f"Register {reg_addr}")
                                data_type = types.get(addr_str, "FLOAT32").upper()
                                # register type map from PyQt6 modes (FC04 -> Input Register, FC03 -> Holding Register)
                                mode_val = modes.get(addr_str, "FC04")
                                reg_type = "Holding Register (FC03)" if "FC03" in mode_val else "Input Register (FC04)"
                                
                                factor = float(factors.get(addr_str, 1.0))
                                op = ops.get(addr_str, "*")
                                multiplier = factor if op == "*" else 1.0
                                divisor = factor if op == "/" else 1.0
                                unit = units.get(addr_str, "")

                                db.add(DBRegister(
                                    device_id=dev.id,
                                    name=reg_name,
                                    address=int(reg_addr),
                                    register_type=reg_type,
                                    data_type=data_type,
                                    multiplier=multiplier,
                                    divisor=divisor,
                                    unit=unit
                                ))
                        db.commit()
                        print("Migrated devices and registers configuration from desktop app.")
                except Exception as e:
                    print(f"Error migrating devices.json: {e}")

        # Sync existing CSV logs if available
        desktop_live_dir = "/home/vicky/praveen-projects/python-desktop-application/logger_app/live"
        if os.path.exists(desktop_live_dir):
            try:
                for file_name in os.listdir(desktop_live_dir):
                    if file_name.endswith(".csv"):
                        src = os.path.join(desktop_live_dir, file_name)
                        dst = os.path.join(LIVE_LOGS_PATH, file_name)
                        if not os.path.exists(dst):
                            shutil.copy2(src, dst)
                print("Synced historical CSV logs from desktop app.")
            except Exception as e:
                print(f"Error syncing CSV logs: {e}")

    finally:
        db.close()

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
