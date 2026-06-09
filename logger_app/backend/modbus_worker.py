"""
modbus_worker.py
PyQt6 QThread-based Modbus polling worker.
Emits signals for new data, log messages, and connection status — never
touches the UI directly so it can safely run on a background thread.
"""

import time
import threading
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient
except ImportError:
    try:
        from pymodbus.client import ModbusTcpClient, ModbusSerialClient
    except ImportError:
        from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient

import pymodbus
PYMODBUS_V3 = pymodbus.__version__.startswith('3')

from .core import (
    decode_float, decode_int, decode_uint, decode_int16, decode_uint16, decode_bcd,
    write_csv, write_alarm_history_csv, write_email_log_csv, DATA_PATH
)


class ModbusWorker(QThread):
    """
    Polls a single Modbus device (TCP or Serial) in the background.

    Signals
    -------
    data_received(str, str)
        (val_id, formatted_value) — emitted for every successfully decoded register.
    log_message(str)
        A human-readable status / error log line.
    connection_status(str, bool)
        (device_key, is_connected) — emitted when connection state changes.
    alert_triggered(dict, float)
        (alert_config_dict, current_value) — emitted when an email-alert condition fires.
    """

    data_received      = pyqtSignal(str, str)   # (val_id, value_str)
    log_message        = pyqtSignal(str)         # log text
    connection_status  = pyqtSignal(str, bool)   # (key, connected)
    alert_triggered    = pyqtSignal(dict, float) # (alert_dict, value)

    # Shared Modbus clients / locks (class-level so multiple workers share one
    # TCP connection per (host, port)).
    _shared_clients: dict = {}
    _client_locks:   dict = {}
    _class_lock = threading.Lock()

    def __init__(self, device: dict, app_ref, parent=None):
        super().__init__(parent)
        self.device     = device
        self.app_ref    = app_ref          # reference to main window for email settings
        self._running   = True
        self._refresh   = threading.Event()

        ip        = device['ip']
        port      = device['port']
        slave     = device.get('slave_id', 1)
        conn_type = device.get('conn_type', 'TCP')

        self.key = f"{ip}:{port}:{slave}" if conn_type == "TCP" else f"{ip}:{slave}"

    # ------------------------------------------------------------------
    def _log(self, msg: str):
        prefix = f"[{self.key}]"
        self.log_message.emit(f"{prefix} {msg}")

    # ------------------------------------------------------------------
    def _get_client(self):
        """Return (shared_client, per_ip_lock), creating them if needed."""
        dev  = self.device
        ip   = dev['ip']
        port = dev['port']
        ct   = dev.get('conn_type', 'TCP')
        key  = (ip, port) if ct == "TCP" else ip

        with ModbusWorker._class_lock:
            if key not in ModbusWorker._shared_clients:
                if ct == "TCP":
                    client = ModbusTcpClient(host=ip, port=port, timeout=5)
                else:
                    baudrate = int(dev.get('baudrate', 9600) or 9600)
                    parity   = dev.get('parity', 'N') or 'N'
                    stopbits = float(dev.get('stopbits', 1) or 1)
                    bytesize = int(dev.get('bytesize', 8) or 8)
                    method   = dev.get('method', 'rtu') or 'rtu'

                    if PYMODBUS_V3:
                        framer = "rtu" if method.lower() == "rtu" else "ascii"
                        client = ModbusSerialClient(
                            port=ip, framer=framer,
                            baudrate=baudrate, parity=parity,
                            stopbits=stopbits, bytesize=bytesize, timeout=2
                        )
                    else:
                        client = ModbusSerialClient(
                            method=method, port=ip,
                            baudrate=baudrate, parity=parity,
                            stopbits=stopbits, bytesize=bytesize, timeout=2
                        )

                ModbusWorker._shared_clients[key] = client

            if key not in ModbusWorker._client_locks:
                ModbusWorker._client_locks[key] = threading.Lock()

        return ModbusWorker._shared_clients[key], ModbusWorker._client_locks[key]

    # ------------------------------------------------------------------
    def run(self):
        dev       = self.device
        ip        = dev['ip']
        port      = dev['port']
        slave     = dev.get('slave_id', 1)
        conn_type = dev.get('conn_type', 'TCP')
        registers = dev['registers']

        self._log("Initializing...")

        try:
            client, lock = self._get_client()
        except Exception as e:
            self._log(f"Initialization Failed: {e}")
            return

        first_run = True

        while self._running:
            with lock:
                try:
                    # ---- Ensure connected ----
                    try:
                        is_connected = client.is_connected()
                    except:
                        is_connected = getattr(client, 'connected', False)

                    if not is_connected:
                        if not client.connect():
                            self._log(f"Connection Failed ❌")
                            self.connection_status.emit(self.key, False)
                            time.sleep(2)
                            continue

                    if first_run:
                        self._log("Connected ✔")
                        self.connection_status.emit(self.key, True)
                        first_run = False

                    # ---- Poll registers ----
                    for reg in registers:
                        if not self._running:
                            break
                        try:
                            dt        = dev.get('types',   {}).get(str(reg), "INT32")
                            reg_mode  = dev.get('modes',   {}).get(str(reg), "FC04")
                            try:
                                divisor = float(dev.get('divisors', {}).get(str(reg), 1.0))
                            except:
                                divisor = 1.0

                            count = 2 if ("32" in dt or dt == "BCD" or "DOUBLE" in dt) else 1
                            kw    = {'device_id' if PYMODBUS_V3 else 'unit': slave}

                            if reg_mode == "FC03":
                                result = client.read_holding_registers(address=reg, count=count, **kw)
                            elif reg_mode == "FC01":
                                result = client.read_coils(address=reg, count=1, **kw)
                            elif reg_mode == "FC02":
                                result = client.read_discrete_inputs(address=reg, count=1, **kw)
                            else:
                                result = client.read_input_registers(address=reg, count=count, **kw)

                            if result is None:
                                self._log(f"TIMEOUT @ {reg}")
                                continue

                            if result.isError():
                                codes = {1: "Illegal Func", 2: "Illegal Addr", 3: "Illegal Data", 4: "Fail"}
                                err = codes.get(getattr(result, 'exception_code', 0), str(result))
                                self._log(f"Read Error @ {reg}: {err}")
                                continue

                            # ---- Decode ----
                            if reg_mode in ["FC01", "FC02"]:
                                value = 1 if result.bits[0] else 0
                            else:
                                if len(result.registers) < count:
                                    self._log(f"Partial Read @ {reg}")
                                    continue

                                if count == 2:
                                    h, l = result.registers[0], result.registers[1]
                                    if "FLOAT32" in dt:
                                        value = decode_float(h, l)
                                    elif "UINT32" in dt or "UNSIGNED DOUBLE" in dt:
                                        value = decode_uint(h, l)
                                    elif dt == "BCD":
                                        value = decode_bcd(h, l)
                                    else:
                                        value, _ = decode_int(h, l)
                                elif dt == "INT16":
                                    value = decode_int16(result.registers[0])
                                elif dt in ["UINT16", "UNSIGNED INT"]:
                                    value = decode_uint16(result.registers[0])
                                else:
                                    value = result.registers[0]

                                # ---- Math ----
                                op     = dev.get('ops',     {}).get(str(reg), "/")
                                factor = float(dev.get('factors', {}).get(str(reg), 1.0))
                                value  = value * factor if op == "*" else value / factor

                                # ---- Decimal scale factor + format ----
                                try:
                                    p_val = dev.get('decimals', {}).get(str(reg), "0.1")
                                    scale = float(p_val) if p_val is not None else 0.1
                                    # If scale looks like an old integer precision (0–4), keep legacy
                                    if scale in (0.0, 1.0, 2.0, 3.0, 4.0) and str(p_val) in ("0","1","2","3","4"):
                                        prec = int(scale)
                                        val_str = f"{float(value):.{prec}f}"
                                    else:
                                        # Multiply raw value by scale factor
                                        value = float(value) * scale
                                        # Derive display precision from scale factor's own decimal places
                                        if '.' in str(p_val):
                                            prec = len(str(p_val).rstrip('0').split('.')[1])
                                        else:
                                            prec = 0
                                        val_str = f"{value:.{prec}f}"
                                except Exception:
                                    val_str = str(value)

                                # ---- Emit & Log ----
                                val_id = (
                                    f"{ip}:{port}:{slave}:{reg}" if conn_type == "TCP"
                                    else f"{ip}:{slave}:{reg}"
                                )
                                self.data_received.emit(val_id, val_str)
                                write_csv(ip, port, slave, reg, val_str)
                                self._log(f"Reg {reg} → {val_str}")

                            # ---- Email Alert Check ----
                            if self.app_ref:
                                for alert in self.app_ref.email_settings.get('alerts', []):
                                    if (str(alert.get('device_ip')) == str(ip) and
                                            str(alert.get('port')) == str(port) and
                                            str(alert.get('slave_id', 1)) == str(slave) and
                                            str(alert.get('reg')) == str(reg)):
                                        try:
                                            thresh   = float(alert.get('threshold'))
                                            cond     = alert.get('condition')
                                            triggered = (
                                                (cond == ">" and value > thresh) or
                                                (cond == "<" and value < thresh) or
                                                (cond == "==" and value == thresh)
                                            )
                                            if triggered:
                                                self.alert_triggered.emit(dict(alert), float(value))
                                        except:
                                            continue

                        except Exception as e:
                            self._log(f"Error @ Reg {reg}: {e}")

                except Exception as e:
                    self._log(f"Global Polling Error: {e}")
                    self.connection_status.emit(self.key, False)

            # Wait for refresh signal or sleep 100ms
            self._refresh.wait(timeout=1.0)
            self._refresh.clear()

        self._log("Polling Stopped")

    # ------------------------------------------------------------------
    def stop(self):
        self._running = False
        self._refresh.set()
        self.quit()

    def trigger_refresh(self):
        self._refresh.set()
