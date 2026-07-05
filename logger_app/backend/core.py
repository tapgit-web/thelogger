import time
import base64
import struct
import threading
import json
import os
import csv
import hashlib
import uuid
import smtplib
import ssl
import requests
import sys
import shutil
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient
except ImportError:
    try:
        from pymodbus.client import ModbusTcpClient, ModbusSerialClient
    except ImportError:
        from pymodbus.client.sync import ModbusTcpClient as ModbusTcpClient
        from pymodbus.client.sync import ModbusSerialClient as ModbusSerialClient

try:
    from pymodbus.framer import FramerRTU as ModbusRtuFramer
except ImportError:
    try:
        from pymodbus.framer.rtu_framer import ModbusRtuFramer
    except ImportError:
        ModbusRtuFramer = None

import pymodbus
PYMODBUS_V3 = pymodbus.__version__.startswith('3')

# =================== PATH RESOLUTION ===================

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_path, relative_path)

# =================== LICENSE CONFIG ===================

API_URL = "http://localhost:3000/activate"
LICENSE_FILE = os.path.join(os.getenv("APPDATA"), "Microsoft", "sys.dat")

def get_hwid():
    try:
        mac = uuid.getnode()
        comp_name = os.environ.get('COMPUTERNAME', 'STATION-01')
        combined = f"{mac}-{comp_name}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16].upper()
    except:
        return "DEFAULT-HWID-001"

def obfuscate_data(data_str):
    key = get_hwid()
    xor_data = "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data_str))
    return base64.b64encode(xor_data.encode()).decode()

def deobfuscate_data(encoded_str):
    try:
        raw_data = base64.b64decode(encoded_str).decode()
        key = get_hwid()
        decoded = "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(raw_data))
        return decoded
    except Exception:
        return None

def save_local_license(key):
    try:
        os.makedirs(os.path.dirname(LICENSE_FILE), exist_ok=True)
        with open(LICENSE_FILE, "w") as f:
            f.write(obfuscate_data(key))
        return True
    except:
        return False

def load_local_license():
    if not os.path.exists(LICENSE_FILE):
        return None
    try:
        with open(LICENSE_FILE, "r") as f:
            content = f.read().strip()
            decoded = deobfuscate_data(content)
            if decoded:
                return decoded
            return content
    except Exception:
        return None

def check_license_online(key):
    try:
        response = requests.post(API_URL, json={"key": key, "hwid": get_hwid()}, timeout=30)
        data = response.json()
        return data.get("valid", False), data.get("msg", "Unknown error")
    except Exception as e:
        return False, f"Connection Error: {str(e)}"

# =================== DATA PATH ===================

if getattr(sys, 'frozen', False):
    DATA_PATH = os.path.join(os.getenv("APPDATA"), "The Logger")
else:
    DATA_PATH = os.path.dirname(os.path.abspath(__file__))
    DATA_PATH = os.path.join(os.path.dirname(DATA_PATH))  # go up to project root

os.makedirs(os.path.join(DATA_PATH, "config"), exist_ok=True)
os.makedirs(os.path.join(DATA_PATH, "live"), exist_ok=True)
os.makedirs(os.path.join(DATA_PATH, "reports"), exist_ok=True)

CONFIG_FILE        = os.path.join(DATA_PATH, "config", "devices.json")
EMAIL_CONFIG_FILE  = os.path.join(DATA_PATH, "config", "email_settings.json")
USERS_FILE         = os.path.join(DATA_PATH, "config", "users.json")
TREND_CONFIG_FILE  = os.path.join(DATA_PATH, "config", "trend_settings.json")

# =================== 30-DAY TRIAL CONFIG & LOGIC ===================

TRIAL_FILE_1 = os.path.join(os.getenv("APPDATA"), "Microsoft", "sys_t.dat")
TRIAL_FILE_2 = os.path.join(DATA_PATH, "config", "sys_t.dat")

def get_trial_status():
    """
    Checks trial files, performs validation, updates last run, and restores missing file if one is deleted.
    Returns: (status, days_left, msg)
      status: "active", "expired", "tampered"
    """
    now = datetime.now()
    
    data_1 = None
    data_2 = None
    
    # Try reading from path 1
    if os.path.exists(TRIAL_FILE_1):
        try:
            with open(TRIAL_FILE_1, "r") as f:
                content = f.read().strip()
            decoded = deobfuscate_data(content)
            if decoded:
                data_1 = json.loads(decoded)
        except:
            pass
            
    # Try reading from path 2
    if os.path.exists(TRIAL_FILE_2):
        try:
            with open(TRIAL_FILE_2, "r") as f:
                content = f.read().strip()
            decoded = deobfuscate_data(content)
            if decoded:
                data_2 = json.loads(decoded)
        except:
            pass

    # If neither exists, initialize new trial
    if data_1 is None and data_2 is None:
        data = {
            "start_date": now.isoformat(),
            "last_run": now.isoformat()
        }
        obfuscated = obfuscate_data(json.dumps(data))
        try:
            os.makedirs(os.path.dirname(TRIAL_FILE_1), exist_ok=True)
            with open(TRIAL_FILE_1, "w") as f:
                f.write(obfuscated)
        except:
            pass
        try:
            os.makedirs(os.path.dirname(TRIAL_FILE_2), exist_ok=True)
            with open(TRIAL_FILE_2, "w") as f:
                f.write(obfuscated)
        except:
            pass
        return "active", 30, "Trial started."

    # If only one exists, restore the other! (Self-healing)
    # If both exist, use the oldest start_date to prevent trial reset by modifying one.
    if data_1 and data_2:
        try:
            start_1 = datetime.fromisoformat(data_1["start_date"])
            start_2 = datetime.fromisoformat(data_2["start_date"])
            start_date = min(start_1, start_2)
            
            last_run_1 = datetime.fromisoformat(data_1["last_run"])
            last_run_2 = datetime.fromisoformat(data_2["last_run"])
            last_run = max(last_run_1, last_run_2)
        except:
            return "expired", 0, "Trial data is corrupt."
    elif data_1:
        try:
            start_date = datetime.fromisoformat(data_1["start_date"])
            last_run = datetime.fromisoformat(data_1["last_run"])
        except:
            return "expired", 0, "Trial data is corrupt."
    else:
        try:
            start_date = datetime.fromisoformat(data_2["start_date"])
            last_run = datetime.fromisoformat(data_2["last_run"])
        except:
            return "expired", 0, "Trial data is corrupt."

    # Tampering check
    if now < last_run:
        return "tampered", 0, "Clock rollback detected."
        
    # Trial duration calculation
    elapsed = now - start_date
    days_left = 30 - elapsed.days
    
    if days_left <= 0:
        return "expired", 0, "Trial period has expired."
        
    # Update and sync both files with current time
    updated_data = {
        "start_date": start_date.isoformat(),
        "last_run": now.isoformat()
    }
    obfuscated = obfuscate_data(json.dumps(updated_data))
    try:
        os.makedirs(os.path.dirname(TRIAL_FILE_1), exist_ok=True)
        with open(TRIAL_FILE_1, "w") as f:
            f.write(obfuscated)
    except:
        pass
    try:
        os.makedirs(os.path.dirname(TRIAL_FILE_2), exist_ok=True)
        with open(TRIAL_FILE_2, "w") as f:
            f.write(obfuscated)
    except:
        pass
        
    return "active", days_left, f"Trial active: {days_left} days remaining."

# =================== CONFIG MIGRATION ===================

def migrate_config_files():
    files = [CONFIG_FILE, EMAIL_CONFIG_FILE, USERS_FILE, TREND_CONFIG_FILE]
    for filepath in files:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    content = f.read().strip()
                if not content:
                    continue
                if deobfuscate_data(content) is None:
                    try:
                        data = json.loads(content)
                        with open(filepath, "w") as f:
                            f.write(obfuscate_data(json.dumps(data, indent=4)))
                    except json.JSONDecodeError:
                        pass
            except:
                pass

migrate_config_files()

# =================== JSON STORAGE ===================

def load_devices():
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, "r") as f:
            content = f.read().strip()
            decoded = deobfuscate_data(content)
            if decoded:
                return json.loads(decoded)
            return json.loads(content)
    except:
        return []

def save_devices(devices):
    with open(CONFIG_FILE, "w") as f:
        f.write(obfuscate_data(json.dumps(devices, indent=4)))

def load_email_settings():
    default = {
        "server_type": "Gmail", "smtp_server": "smtp.gmail.com", "smtp_port": "587",
        "imap_server": "imap.gmail.com", "imap_port": "993",
        "pop3_server": "pop.gmail.com", "pop3_port": "995",
        "sender_email": "", "sender_password": "", "recipient_email": "",
        "subject": "THE LOGGER System Alert", "email_enabled": True, "alerts": []
    }
    if not os.path.exists(EMAIL_CONFIG_FILE):
        return default
    try:
        with open(EMAIL_CONFIG_FILE, "r") as f:
            content = f.read().strip()
            decoded = deobfuscate_data(content)
            data = json.loads(decoded if decoded else content)
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
    except:
        return default

def save_email_settings(settings):
    with open(EMAIL_CONFIG_FILE, "w") as f:
        f.write(obfuscate_data(json.dumps(settings, indent=4)))

def load_users():
    h = hashlib.sha256("admin".encode()).hexdigest()
    default_admin = {"admin": {"password": h, "permissions": ["live_data", "add_device", "live_log", "email_config", "email_smtp_config", "export_data", "data_trends", "user_manager"], "is_admin": True}}
    if not os.path.exists(USERS_FILE):
        save_users(default_admin)
        return default_admin
    try:
        with open(USERS_FILE, "r") as f:
            content = f.read().strip()
            decoded = deobfuscate_data(content)
            users = json.loads(decoded if decoded else content)
            if "admin" in users:
                all_perms = ["live_data", "add_device", "live_log", "email_config", "email_smtp_config", "export_data", "data_trends", "user_manager"]
                for p in all_perms:
                    if p not in users["admin"]["permissions"]:
                        users["admin"]["permissions"].append(p)
            return users
    except Exception as e:
        print(f"User load recovery: {e}")
        return default_admin

def save_users(users):
    with open(USERS_FILE, "w") as f:
        f.write(obfuscate_data(json.dumps(users, indent=4)))

def load_trend_settings():
    default = {"low_limit": "", "upper_limit": "", "visible_condition": "Both Limits", "decimal_places": "3"}
    if not os.path.exists(TREND_CONFIG_FILE):
        return default
    try:
        with open(TREND_CONFIG_FILE, "r") as f:
            content = f.read().strip()
            decoded = deobfuscate_data(content)
            data = json.loads(decoded if decoded else content)
            if "decimal_places" not in data:
                data["decimal_places"] = "3"
            return data
    except:
        return default

def save_trend_settings(settings):
    with open(TREND_CONFIG_FILE, "w") as f:
        f.write(obfuscate_data(json.dumps(settings, indent=4)))

# =================== CSV LOGGING ===================

def csv_filename(ip, port, slave_id=1):
    date_str = datetime.now().strftime("%Y-%m-%d")
    clean_ip = ip.replace('.', '_').replace(':', '_').replace('/', '_').replace('\\', '_')
    return os.path.join(DATA_PATH, "live", f"{clean_ip}_{port}_s{slave_id}_{date_str}.csv")

def write_csv(ip, port, slave_id, reg, value):
    filename = csv_filename(ip, port, slave_id)
    exists = os.path.exists(filename)
    try:
        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["Timestamp", "IP", "Port", "SlaveID", "Register", "Value"])
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip, port, slave_id, reg, value])
    except:
        pass

def write_alarm_history_csv(dev_name, reg_name, reg_addr, value, condition, threshold):
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(DATA_PATH, "live", f"Alarm_History_{date_str}.csv")
    exists = os.path.exists(filename)
    try:
        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["Timestamp", "Device Name", "Field Name", "Addr", "Reading Value", "Condition", "Threshold"])
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), dev_name, reg_name, reg_addr, value, condition, threshold])
    except:
        pass

def write_email_log_csv(dev_name, field_name, recipient, status):
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(DATA_PATH, "live", f"Email_Logs_{date_str}.csv")
    exists = os.path.exists(filename)
    try:
        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["Timestamp", "Device Name", "Field Name", "Recipient", "Status"])
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), dev_name, field_name, recipient, status])
    except:
        pass

# =================== FLOAT DECODING ===================

def decode_int(h, l):
    raw = struct.pack(">HH", h, l)
    int_value = struct.unpack(">i", raw)[0]
    return int_value, raw.hex().upper()

def decode_float(h, l):
    raw = struct.pack(">HH", h, l)
    return struct.unpack(">f", raw)[0]

def decode_uint(h, l):
    raw = struct.pack(">HH", h, l)
    return struct.unpack(">I", raw)[0]

def decode_int16(h):
    raw = struct.pack(">H", h)
    return struct.unpack(">h", raw)[0]

def decode_uint16(h):
    return h

def decode_bcd(h, l):
    s = f"{h:04x}{l:04x}"
    try:
        return int(s)
    except:
        return 0
