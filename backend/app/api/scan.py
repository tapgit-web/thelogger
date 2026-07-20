import socket
import concurrent.futures
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/scan", tags=["scan"])

import time

class NetInterfaceInfo(BaseModel):
    name: str
    ip: str
    subnet: str
    is_primary: bool

class NetInfoResponse(BaseModel):
    primary_subnet: str
    interfaces: List[NetInterfaceInfo]

class IPScanRequest(BaseModel):
    subnet: str  # e.g. "127.0.0.1", "192.168.0", "192.168.0.0/24", or comma-separated "192.168.0, 192.168.1"
    ports: List[int] = [502, 5020, 5021]

class IPScanResult(BaseModel):
    ip: str
    port: int
    status: str
    latency_ms: Optional[float] = None

class SlaveScanRequest(BaseModel):
    ip: str
    port: int
    start_id: int = 1
    end_id: int = 10

class SlaveScanResult(BaseModel):
    ip: str
    port: int
    active_slave_ids: List[int]

@router.get("/net-info", response_model=NetInfoResponse)
def get_net_info(current_user = Depends(get_current_user)):
    interfaces: List[NetInterfaceInfo] = []
    primary_ip = None

    # Detect primary local LAN IP via UDP socket connect
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
    except Exception:
        pass

    detected_ips: List[str] = []
    try:
        hostname = socket.gethostname()
        addrs = socket.gethostbyname_ex(hostname)[2]
        for ip in addrs:
            if not ip.startswith("169.254") and ip not in detected_ips:
                detected_ips.append(ip)
    except Exception:
        pass

    if primary_ip and primary_ip not in detected_ips and not primary_ip.startswith("127."):
        detected_ips.insert(0, primary_ip)

    if "127.0.0.1" not in detected_ips:
        detected_ips.append("127.0.0.1")

    primary_subnet = "127.0.0.1"

    for ip in detected_ips:
        parts = ip.split(".")
        if len(parts) == 4 and ip != "127.0.0.1":
            subnet = f"{parts[0]}.{parts[1]}.{parts[2]}"
            is_primary = (ip == primary_ip)
            if is_primary:
                primary_subnet = subnet
            name = f"LAN ({ip})" if is_primary else f"Interface ({ip})"
            interfaces.append(NetInterfaceInfo(name=name, ip=ip, subnet=subnet, is_primary=is_primary))
        elif ip == "127.0.0.1":
            is_primary = (primary_ip is None or primary_ip == "127.0.0.1")
            interfaces.append(NetInterfaceInfo(name="Localhost / Simulator (127.0.0.1)", ip="127.0.0.1", subnet="127.0.0.1", is_primary=is_primary))

    if primary_subnet == "127.0.0.1":
        non_loopback = [i for i in interfaces if i.ip != "127.0.0.1"]
        if non_loopback:
            primary_subnet = non_loopback[0].subnet
            non_loopback[0].is_primary = True

    return NetInfoResponse(primary_subnet=primary_subnet, interfaces=interfaces)

def check_ip_port(ip: str, port: int) -> Optional[IPScanResult]:
    try:
        t0 = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.15)
            result = s.connect_ex((ip, port))
            if result == 0:
                latency = round((time.time() - t0) * 1000, 1)
                return IPScanResult(ip=ip, port=port, status="active", latency_ms=latency)
    except Exception:
        pass
    return None

def parse_ips_to_scan(subnet_input: str) -> List[str]:
    subnet_input = (subnet_input or "").strip()
    if not subnet_input or subnet_input == "127.0.0.1":
        return ["127.0.0.1"]
    
    ips: List[str] = []
    chunks = [c.strip() for c in subnet_input.split(",") if c.strip()]
    for chunk in chunks:
        if "/" in chunk:
            chunk = chunk.split("/")[0].strip()
            
        parts = chunk.split(".")
        if len(parts) >= 3:
            prefix = f"{parts[0]}.{parts[1]}.{parts[2]}"
            for i in range(1, 255):
                ip_str = f"{prefix}.{i}"
                if ip_str not in ips:
                    ips.append(ip_str)
        else:
            if chunk not in ips:
                ips.append(chunk)
                
    return ips

@router.post("/ips", response_model=List[IPScanResult])
def scan_ips(req: IPScanRequest, current_user = Depends(get_current_user)):
    ips_to_scan = parse_ips_to_scan(req.subnet)
        
    results = []
    # Scale concurrency with 120 worker threads for multi-host subnets
    with concurrent.futures.ThreadPoolExecutor(max_workers=120) as executor:
        futures = []
        for ip in ips_to_scan:
            for port in req.ports:
                futures.append(executor.submit(check_ip_port, ip, port))
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                
    # Sort results by IP integer value and port for clean ordering
    def ip_sort_key(item: IPScanResult):
        try:
            octets = [int(x) for x in item.ip.split(".")]
            return (octets, item.port)
        except Exception:
            return ([0, 0, 0, 0], item.port)

    results.sort(key=ip_sort_key)
    return results

def query_slave_frame(s: socket.socket, slave_id: int) -> bool:
    try:
        packet = bytearray([
            0x00, slave_id & 0xFF,  # Transaction ID
            0x00, 0x00,             # Protocol ID
            0x00, 0x06,             # Length
            slave_id & 0xFF,        # Unit ID (Slave ID)
            0x03,                   # Function Code (Read Holding Register)
            0x00, 0x00,             # Start Address 0
            0x00, 0x01              # Quantity 1
        ])
        s.sendall(packet)
        response = s.recv(1024)
        if len(response) >= 7:
            resp_unit_id = response[6]
            # Strict MBAP header verification: The responding Unit ID must match the requested Slave ID
            if resp_unit_id == (slave_id & 0xFF):
                return True
    except Exception:
        pass
    return False

@router.post("/slaves", response_model=SlaveScanResult)
def scan_slaves(req: SlaveScanRequest, current_user = Depends(get_current_user)):
    active_slaves = []
    
    # 1. Try single persistent socket connection (preferred for hardware RS485/Ethernet gateways)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.8)
            s.connect((req.ip, req.port))
            for slave_id in range(req.start_id, req.end_id + 1):
                if query_slave_frame(s, slave_id):
                    active_slaves.append(slave_id)
    except Exception:
        pass

    # 2. Fallback to discrete socket connections for any slave IDs missed due to socket resets
    remaining = [sid for sid in range(req.start_id, req.end_id + 1) if sid not in active_slaves]
    for slave_id in remaining:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.8)
                s.connect((req.ip, req.port))
                if query_slave_frame(s, slave_id):
                    active_slaves.append(slave_id)
        except Exception:
            pass

    active_slaves.sort()
    return SlaveScanResult(ip=req.ip, port=req.port, active_slave_ids=active_slaves)
