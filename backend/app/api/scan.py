import socket
import concurrent.futures
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/scan", tags=["scan"])

class IPScanRequest(BaseModel):
    subnet: str  # e.g. "127.0.0.1" or "192.168.0" (first three octets)
    ports: List[int] = [502, 5020, 5021]

class IPScanResult(BaseModel):
    ip: str
    port: int
    status: str

class SlaveScanRequest(BaseModel):
    ip: str
    port: int
    start_id: int = 1
    end_id: int = 10

class SlaveScanResult(BaseModel):
    ip: str
    port: int
    active_slave_ids: List[int]

def check_ip_port(ip: str, port: int) -> Optional[IPScanResult]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            result = s.connect_ex((ip, port))
            if result == 0:
                return IPScanResult(ip=ip, port=port, status="active")
    except Exception:
        pass
    return None

@router.post("/ips", response_model=List[IPScanResult])
def scan_ips(req: IPScanRequest, current_user = Depends(get_current_user)):
    if req.subnet == "127.0.0.1" or not req.subnet:
        ips_to_scan = ["127.0.0.1"]
    elif req.subnet.count(".") == 2:  # e.g. "192.168.0"
        ips_to_scan = [f"{req.subnet}.{i}" for i in range(1, 255)]
    else:
        ips_to_scan = [req.subnet]
        
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for ip in ips_to_scan:
            for port in req.ports:
                futures.append(executor.submit(check_ip_port, ip, port))
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                
    results.sort(key=lambda x: (x.ip, x.port))
    return results

def check_slave_id(ip: str, port: int, slave_id: int) -> Optional[int]:
    try:
        # Build standard Modbus TCP frame (FC03 Read Holding Register 0, quantity 1)
        packet = bytearray([
            0x00, 0x01,  # Transaction ID
            0x00, 0x00,  # Protocol ID
            0x00, 0x06,  # Length
            slave_id,    # Unit ID (Slave ID)
            0x03,        # Function Code
            0x00, 0x00,  # Start Register High/Low
            0x00, 0x01   # Quantity High/Low
        ])
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            s.connect((ip, port))
            s.sendall(packet)
            response = s.recv(1024)
            
            if len(response) >= 9:
                resp_fc = response[7]
                # Any Modbus TCP response (success or exception) indicates that the Slave ID is active
                if resp_fc == 0x03 or resp_fc == 0x83:
                    return slave_id
    except Exception:
        pass
    return None

@router.post("/slaves", response_model=SlaveScanResult)
def scan_slaves(req: SlaveScanRequest, current_user = Depends(get_current_user)):
    active_slaves = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(check_slave_id, req.ip, req.port, slave_id): slave_id
            for slave_id in range(req.start_id, req.end_id + 1)
        }
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res is not None:
                active_slaves.append(res)
                
    active_slaves.sort()
    return SlaveScanResult(ip=req.ip, port=req.port, active_slave_ids=active_slaves)
