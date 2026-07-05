import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import app.services.modbus_worker as worker

router = APIRouter(tags=["polling"])

@router.post("/api/polling/toggle")
def toggle_polling():
    if worker.is_polling:
        worker.stop_polling()
    else:
        worker.start_polling(asyncio.get_event_loop())
    return {"is_polling": worker.is_polling}

@router.websocket("/api/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await worker.manager.connect(websocket)
    try:
        # Send initial data immediately
        initial_payload = {
            "type": "telemetry",
            "is_polling": worker.is_polling,
            "data": list(worker.latest_readings.values())
        }
        await websocket.send_json(initial_payload)
        
        while True:
            # Maintain connection
            await websocket.receive_text()
    except WebSocketDisconnect:
        worker.manager.disconnect(websocket)
    except Exception:
        worker.manager.disconnect(websocket)
