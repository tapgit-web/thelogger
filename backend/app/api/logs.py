import os
import csv
import glob
from fastapi import APIRouter, Depends, Query
from typing import List
from pydantic import BaseModel

from app.core.config import LIVE_LOGS_PATH
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/logs", tags=["logs"])

class AlarmLogEntry(BaseModel):
    timestamp: str
    device_name: str
    field_name: str
    address: int
    value: float
    condition: str
    threshold: float

class EmailLogEntry(BaseModel):
    timestamp: str
    device_name: str
    field_name: str
    recipient: str
    status: str

@router.get("/alarms", response_model=List[AlarmLogEntry])
def get_alarm_logs(
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user)
):
    pattern = os.path.join(LIVE_LOGS_PATH, "Alarm_History_*.csv")
    files = glob.glob(pattern)
    files.sort(reverse=True)
    
    logs = []
    for file_path in files:
        if len(logs) >= limit:
            break
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                file_logs = []
                for row in reader:
                    try:
                        file_logs.append(AlarmLogEntry(
                            timestamp=row.get("Timestamp", ""),
                            device_name=row.get("Device Name", ""),
                            field_name=row.get("Field Name", ""),
                            address=int(row.get("Addr", 0)),
                            value=float(row.get("Reading Value", 0.0)),
                            condition=row.get("Condition", ""),
                            threshold=float(row.get("Threshold", 0.0))
                        ))
                    except Exception:
                        continue
                file_logs.sort(key=lambda x: x.timestamp, reverse=True)
                logs.extend(file_logs)
        except Exception:
            continue
            
    logs.sort(key=lambda x: x.timestamp, reverse=True)
    return logs[:limit]

@router.get("/emails", response_model=List[EmailLogEntry])
def get_email_logs(
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user)
):
    pattern = os.path.join(LIVE_LOGS_PATH, "Email_Logs_*.csv")
    files = glob.glob(pattern)
    files.sort(reverse=True)
    
    logs = []
    for file_path in files:
        if len(logs) >= limit:
            break
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                file_logs = []
                for row in reader:
                    try:
                        file_logs.append(EmailLogEntry(
                            timestamp=row.get("Timestamp", ""),
                            device_name=row.get("Device Name", ""),
                            field_name=row.get("Field Name", ""),
                            recipient=row.get("Recipient", ""),
                            status=row.get("Status", "")
                        ))
                    except Exception:
                        continue
                file_logs.sort(key=lambda x: x.timestamp, reverse=True)
                logs.extend(file_logs)
        except Exception:
            continue
            
    logs.sort(key=lambda x: x.timestamp, reverse=True)
    return logs[:limit]
