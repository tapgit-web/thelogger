import os
import csv
import time
import threading
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from fastapi import WebSocket

# Try imports for pymodbus client
try:
    from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient
except ImportError:
    try:
        from pymodbus.client import ModbusTcpClient, ModbusSerialClient
    except ImportError:
        from pymodbus.client.sync import ModbusTcpClient as ModbusTcpClient
        from pymodbus.client.sync import ModbusSerialClient as ModbusSerialClient

from app.core import SessionLocal, LIVE_LOGS_PATH, MODBUS_OVERRIDE_HOST, MODBUS_OVERRIDE_PORT
from app.models import DBDevice, DBRegister, DBEmailSettings
from app.utils import (
    send_email, decode_int16, decode_uint16, decode_int32, decode_uint32, decode_float32, decode_bcd
)

# Global Telemetry & Polling State
is_polling = False
polling_thread = None
latest_readings: Dict[int, Dict[str, Any]] = {}  # maps register_id -> reading dict
active_alarms: Dict[int, Dict[str, bool]] = {}  # maps register_id -> {"low": bool, "high": bool}
client_locks = {}
shared_clients = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

def get_modbus_client(device: DBDevice):
    host = MODBUS_OVERRIDE_HOST if (device.connection_type == "TCP" and MODBUS_OVERRIDE_HOST) else device.host
    port = MODBUS_OVERRIDE_PORT if (device.connection_type == "TCP" and MODBUS_OVERRIDE_PORT) else device.port

    conn_key = f"{device.connection_type}_{host or device.com_port}_{port or device.baudrate}"
    if conn_key not in client_locks:
        client_locks[conn_key] = threading.Lock()
    
    with client_locks[conn_key]:
        if conn_key in shared_clients:
            client = shared_clients[conn_key]
            # Check connection, reconnect if needed
            if not client.is_socket_open():
                client.connect()
            return client

        if device.connection_type == "TCP":
            client = ModbusTcpClient(host, port=port, timeout=3)
        else:
            # RTU
            client = ModbusSerialClient(
                method="rtu",
                port=device.com_port,
                baudrate=device.baudrate,
                parity=device.parity,
                bytesize=device.bytesize,
                stopbits=device.stopbits,
                timeout=3
            )
        client.connect()
        shared_clients[conn_key] = client
        return client

def write_live_csv(device: DBDevice, register: DBRegister, value: float):
    host = MODBUS_OVERRIDE_HOST if (device.connection_type == "TCP" and MODBUS_OVERRIDE_HOST) else device.host
    port_or_baud = MODBUS_OVERRIDE_PORT if (device.connection_type == "TCP" and MODBUS_OVERRIDE_PORT) else (device.port or device.baudrate or 0)

    date_str = datetime.now().strftime("%Y-%m-%d")
    clean_ip = (host or device.com_port or "unknown").replace('.', '_').replace(':', '_').replace('/', '_').replace('\\', '_')
    slave_id = getattr(device, "slave_id", 1)
    
    filename = os.path.join(LIVE_LOGS_PATH, f"{clean_ip}_{port_or_baud}_s{slave_id}_{date_str}.csv")
    exists = os.path.exists(filename)
    try:
        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["Timestamp", "IP", "Port", "SlaveID", "Register", "Value"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                host or device.com_port,
                port_or_baud,
                slave_id,
                register.address,
                value
            ])
    except Exception as e:
        print(f"CSV Logging Error: {e}")

def log_alarm_history(device_name: str, reg_name: str, address: int, value: float, condition: str, threshold: float):
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(LIVE_LOGS_PATH, f"Alarm_History_{date_str}.csv")
    exists = os.path.exists(filename)
    try:
        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["Timestamp", "Device Name", "Field Name", "Addr", "Reading Value", "Condition", "Threshold"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                device_name,
                reg_name,
                address,
                value,
                condition,
                threshold
            ])
    except Exception as e:
        print(f"Alarm Logging Error: {e}")

def log_email_dispatch(device_name: str, reg_name: str, recipient: str, status: str):
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(LIVE_LOGS_PATH, f"Email_Logs_{date_str}.csv")
    exists = os.path.exists(filename)
    try:
        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["Timestamp", "Device Name", "Field Name", "Recipient", "Status"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                device_name,
                reg_name,
                recipient,
                status
            ])
    except Exception as e:
        print(f"Email Logging Error: {e}")

def check_alarm_limits(device: DBDevice, register: DBRegister, value: float, smtp_settings: DBEmailSettings):
    reg_id = register.id
    if reg_id not in active_alarms:
        active_alarms[reg_id] = {"low": False, "high": False}

    alarm_state = active_alarms[reg_id]

    # Check Low Limit
    if register.limit_min is not None:
        if value < register.limit_min:
            if not alarm_state["low"]:
                alarm_state["low"] = True
                # Trigger Alarm!
                log_alarm_history(device.name, register.name, register.address, value, "<", register.limit_min)
                if smtp_settings:
                    subj = f"ALERT: {device.name} - {register.name} low limit breached"
                    body = f"Device: {device.name}\nRegister: {register.name} (Addr: {register.address})\nReading: {value} {register.unit}\nLimit: < {register.limit_min}\nTimestamp: {datetime.now()}"
                    ok = send_email(subj, body, smtp_settings)
                    log_email_dispatch(device.name, register.name, smtp_settings.receiver_email, "SUCCESS" if ok else "FAILED")
        else:
            alarm_state["low"] = False

    # Check High Limit
    if register.limit_max is not None:
        if value > register.limit_max:
            if not alarm_state["high"]:
                alarm_state["high"] = True
                # Trigger Alarm!
                log_alarm_history(device.name, register.name, register.address, value, ">", register.limit_max)
                if smtp_settings:
                    subj = f"ALERT: {device.name} - {register.name} high limit breached"
                    body = f"Device: {device.name}\nRegister: {register.name} (Addr: {register.address})\nReading: {value} {register.unit}\nLimit: > {register.limit_max}\nTimestamp: {datetime.now()}"
                    ok = send_email(subj, body, smtp_settings)
                    log_email_dispatch(device.name, register.name, smtp_settings.receiver_email, "SUCCESS" if ok else "FAILED")
        else:
            alarm_state["high"] = False

def poll_device_registers(client, device: DBDevice, registers: List[DBRegister], smtp_settings: DBEmailSettings):
    # Sort registers by address to optimize read requests if needed
    for reg in registers:
        slave_id = getattr(device, "slave_id", 1)
        value = None
        status = "failed"
        
        try:
            # Determine read function and count
            is_input = "Input Register" in reg.register_type
            is_holding = "Holding Register" in reg.register_type
            is_coil = "Coil" in reg.register_type
            is_discrete = "Discrete Input" in reg.register_type

            is_32bit = reg.data_type in ["INT32", "UINT32", "FLOAT32", "BCD"]
            count = 2 if is_32bit else 1

            if is_coil:
                res = client.read_coils(reg.address, 1, unit=slave_id)
                if not res.isError():
                    value = 1.0 if res.bits[0] else 0.0
                    status = "success"
            elif is_discrete:
                res = client.read_discrete_inputs(reg.address, 1, unit=slave_id)
                if not res.isError():
                    value = 1.0 if res.bits[0] else 0.0
                    status = "success"
            elif is_input or is_holding:
                if is_input:
                    res = client.read_input_registers(reg.address, count, unit=slave_id)
                else:
                    res = client.read_holding_registers(reg.address, count, unit=slave_id)

                if not res.isError():
                    regs_list = res.registers
                    if is_32bit and len(regs_list) >= 2:
                        h, l = regs_list[0], regs_list[1]
                        if reg.data_type == "FLOAT32":
                            value = decode_float32(h, l)
                        elif reg.data_type == "INT32":
                            value = decode_int32(h, l)
                        elif reg.data_type == "UINT32":
                            value = decode_uint32(h, l)
                        elif reg.data_type == "BCD":
                            value = decode_bcd(h, l)
                    elif not is_32bit and len(regs_list) >= 1:
                        h = regs_list[0]
                        if reg.data_type == "INT16":
                            value = decode_int16(h)
                        else:
                            # UINT16
                            value = decode_uint16(h)
                    status = "success"

            if status == "success" and value is not None:
                # Apply math transformation
                value = (value * reg.multiplier) / reg.divisor
                
                # Log reading
                write_live_csv(device, reg, value)
                
                # Check alarms
                check_alarm_limits(device, reg, value, smtp_settings)

        except Exception as ex:
            print(f"Modbus polling error for {device.name} reg {reg.address}: {ex}")
            status = "failed"

        # Update latest readings cache
        latest_readings[reg.id] = {
            "id": reg.id,
            "name": reg.name,
            "device_name": device.name,
            "value": round(value, 4) if value is not None else 0.0,
            "unit": reg.unit,
            "register_type": reg.register_type,
            "address": reg.address,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "slave_id": slave_id
        }

def background_polling_worker(loop):
    global is_polling
    print("Background polling worker started.")
    
    while is_polling:
        db = SessionLocal()
        try:
            devices = db.query(DBDevice).all()
            smtp_settings = db.query(DBEmailSettings).filter_by(id=1).first()

            for dev in devices:
                if not is_polling:
                    break
                
                regs = db.query(DBRegister).filter_by(device_id=dev.id).all()
                if not regs:
                    continue

                try:
                    client = get_modbus_client(dev)
                    poll_device_registers(client, dev, regs, smtp_settings)
                except Exception as e:
                    print(f"Could not connect or poll device {dev.name}: {e}")
                    # Mark all registers as failed
                    for reg in regs:
                        latest_readings[reg.id] = {
                            "id": reg.id,
                            "name": reg.name,
                            "device_name": dev.name,
                            "value": 0.0,
                            "unit": reg.unit,
                            "register_type": reg.register_type,
                            "address": reg.address,
                            "status": "failed",
                            "timestamp": datetime.now().isoformat(),
                            "slave_id": getattr(dev, "slave_id", 1)
                        }

            # Broadcast latest telemetry to WebSockets
            if latest_readings:
                payload = {
                    "type": "telemetry",
                    "is_polling": is_polling,
                    "data": list(latest_readings.values())
                }
                asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)

        except Exception as e:
            print(f"Error in polling worker: {e}")
        finally:
            db.close()
        
        # Sleep interval (2 seconds)
        time.sleep(2)
        
    print("Background polling worker stopped.")

def start_polling(loop):
    global is_polling, polling_thread
    if is_polling:
        return
    is_polling = True
    polling_thread = threading.Thread(target=background_polling_worker, args=(loop,), daemon=True)
    polling_thread.start()

def stop_polling():
    global is_polling
    is_polling = False
    # Clean up clients
    for key, client in list(shared_clients.items()):
        try:
            client.close()
        except:
            pass
    shared_clients.clear()
