import time
import threading
import json
import os
import csv
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from database import SessionLocal
import models
from modbus_decoder import (
    decode_int, decode_float, decode_uint, decode_int16, decode_uint16, decode_bcd
)

# PyModbus Import Compatibility
try:
    from pymodbus.client import ModbusTcpClient, ModbusSerialClient
except ImportError:
    from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient

# Global live readings storage (in-memory cache)
live_readings = []
is_polling_active = False
polling_threads = {}
threads_control = {} # device_id -> active flag

def send_alert_email(register_name, device_name, value, unit, bound, limit):
    db = SessionLocal()
    try:
        settings = db.query(models.SmtpSettings).first()
        if not settings:
            return
        
        subject = f"⚠️ ALARM TRIGGERED: {register_name} on {device_name}"
        body = f"""
        THE LOGGER Alert Notification
        -----------------------------
        Device: {device_name}
        Register: {register_name}
        Current Value: {value} {unit}
        Condition: {bound} limit breached ({limit} {unit})
        Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        msg = MIMEMultipart()
        msg['From'] = settings.sender_email
        msg['To'] = settings.receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        if settings.use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port, context=context) as server:
                server.login(settings.username, settings.password)
                server.sendmail(settings.sender_email, settings.receiver_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.login(settings.username, settings.password)
                server.sendmail(settings.sender_email, settings.receiver_email, msg.as_string())
        print(f"Alert email sent successfully to {settings.receiver_email}")
    except Exception as e:
        print(f"Error sending email alert: {e}")
    finally:
        db.close()

def poll_device_worker(device_id, control):
    global live_readings
    db = SessionLocal()
    
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        db.close()
        return

    print(f"Starting Modbus poll worker for device: {device.name}")
    
    # Initialize Modbus Client
    client = None
    if device.connection_type == "TCP":
        client = ModbusTcpClient(host=device.host, port=device.port, timeout=3)
    else:
        # Map parity
        parity_map = {"N": "N", "E": "E", "O": "O"}
        client = ModbusSerialClient(
            port=device.com_port,
            baudrate=device.baudrate,
            parity=parity_map.get(device.parity, "N"),
            bytesize=device.bytesize or 8,
            stopbits=device.stopbits or 1,
            timeout=3
        )

    # Cache for tracking email alert cooldowns (to prevent spamming)
    last_alert_time = {} # register_id -> timestamp

    while control.get("active", False):
        try:
            # Refresh device registers definitions from DB
            db.close()
            db = SessionLocal()
            device = db.query(models.Device).filter(models.Device.id == device_id).first()
            if not device or not device.registers:
                time.sleep(2)
                continue

            if not client.connected:
                client.connect()
                if not client.connected:
                    # Update local state as error for all device registers
                    for r in device.registers:
                        update_live_reading(r, "Read Error (No Connection)", "error")
                    time.sleep(3)
                    continue

            # Poll each register
            for reg in device.registers:
                if not control.get("active", False):
                    break

                try:
                    dt = reg.data_type
                    reg_mode = "FC03" if "FC03" in reg.register_type else "FC04" if "FC04" in reg.register_type else "FC01" if "FC01" in reg.register_type else "FC02"
                    count = 2 if ("32" in dt or dt == "BCD") else 1
                    
                    # Fetch value
                    result = None
                    if reg_mode == "FC03":
                        result = client.read_holding_registers(address=reg.address, count=count, slave=1)
                    elif reg_mode == "FC04":
                        result = client.read_input_registers(address=reg.address, count=count, slave=1)
                    elif reg_mode == "FC01":
                        result = client.read_coils(address=reg.address, count=1, slave=1)
                    elif reg_mode == "FC02":
                        result = client.read_discrete_inputs(address=reg.address, count=1, slave=1)

                    if result is None or result.isError():
                        update_live_reading(reg, "Error", "error")
                        continue

                    # Decode value
                    if reg_mode in ["FC01", "FC02"]:
                        value = 1 if result.bits[0] else 0
                    else:
                        if len(result.registers) < count:
                            update_live_reading(reg, "Partial Read", "error")
                            continue

                        if count == 2:
                            h, l = result.registers[0], result.registers[1]
                            if "FLOAT32" in dt:
                                value = decode_float(h, l)
                            elif "UINT32" in dt:
                                value = decode_uint(h, l)
                            elif dt == "BCD":
                                value = decode_bcd(h, l)
                            else:
                                value = decode_int(h, l)
                        elif dt == "INT16":
                            value = decode_int16(result.registers[0])
                        else:
                            value = decode_uint16(result.registers[0])

                    # Scaling Math
                    scaled_value = (value * reg.multiplier) / reg.divisor
                    # Format float values nicely
                    if isinstance(scaled_value, float):
                        scaled_value = round(scaled_value, 2)

                    # Update database reading (for trends)
                    new_reading = models.Reading(register_id=reg.id, value=scaled_value, timestamp=datetime.utcnow())
                    db.add(new_reading)
                    db.commit()

                    # Write to Daily CSV
                    write_to_csv_log(device.name, reg.name, reg.address, scaled_value, reg.unit)

                    # Check limit violations and send email notifications
                    check_limits_and_alert(reg, device.name, scaled_value, last_alert_time)

                    # Cache state
                    update_live_reading(reg, scaled_value, "success")

                except Exception as register_error:
                    print(f"Error reading register {reg.name}: {register_error}")
                    update_live_reading(reg, "Exception Error", "error")

            time.sleep(1)

        except Exception as device_error:
            print(f"Poll worker connection error on device {device_id}: {device_error}")
            time.sleep(2)

    if client:
        client.close()
    db.close()
    print(f"Modbus poll worker stopped for device: {device_id}")

def update_live_reading(reg, value, status):
    global live_readings
    # Thread-safe lookup & update
    for r in live_readings:
        if r["id"] == reg.id:
            r["value"] = value
            r["status"] = status
            r["timestamp"] = datetime.now().isoformat()
            return
            
    # If not found, insert new entry
    live_readings.append({
        "id": reg.id,
        "name": reg.name,
        "device_name": reg.device.name,
        "value": value,
        "unit": reg.unit,
        "register_type": reg.register_type,
        "address": reg.address,
        "status": status,
        "timestamp": datetime.now().isoformat()
    })

def write_to_csv_log(device_name, register_name, address, value, unit):
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_dir = "./live"
        os.makedirs(log_dir, exist_ok=True)
        file_path = os.path.join(log_dir, f"log_{today_str}.csv")
        
        file_exists = os.path.exists(file_path)
        with open(file_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Device", "Register", "Address", "Value", "Unit"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                device_name,
                register_name,
                address,
                value,
                unit
            ])
    except Exception as e:
        print(f"CSV log write failed: {e}")

def check_limits_and_alert(reg, device_name, value, last_alert_time):
    now = time.time()
    # Check limit boundaries
    alert_triggered = False
    bound = ""
    limit = 0.0

    if reg.limit_min is not None and value < reg.limit_min:
        alert_triggered = True
        bound = "LOW"
        limit = reg.limit_min
    elif reg.limit_max is not None and value > reg.limit_max:
        alert_triggered = True
        bound = "HIGH"
        limit = reg.limit_max

    if alert_triggered:
        # Simple alert throttling: limit 1 email per register every 5 minutes
        last_alert = last_alert_time.get(reg.id, 0)
        if now - last_alert > 300:
            last_alert_time[reg.id] = now
            # Dispatch background worker email thread to avoid blocking polling
            email_thread = threading.Thread(
                target=send_alert_email,
                args=(reg.name, device_name, value, reg.unit, bound, limit),
                daemon=True
            )
            email_thread.start()

def start_polling():
    global is_polling_active, polling_threads, threads_control, live_readings
    if is_polling_active:
        return
        
    db = SessionLocal()
    devices = db.query(models.Device).all()
    db.close()
    
    if not devices:
        print("No Modbus devices configured to poll.")
        return

    # Clear cached telemetry on start
    live_readings = []
    is_polling_active = True

    for dev in devices:
        threads_control[dev.id] = {"active": True}
        thread = threading.Thread(
            target=poll_device_worker,
            args=(dev.id, threads_control[dev.id]),
            daemon=True
        )
        polling_threads[dev.id] = thread
        thread.start()

def stop_polling():
    global is_polling_active, polling_threads, threads_control
    if not is_polling_active:
        return

    is_polling_active = False
    
    # Signalling worker threads to shutdown
    for dev_id, control in threads_control.items():
        control["active"] = False

    # Block join with reasonable timeouts
    for dev_id, thread in polling_threads.items():
        thread.join(timeout=2)
        
    polling_threads = {}
    threads_control = {}
    print("Modbus polling supervisor stopped.")
