# backend/main.py
import asyncio
import json
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        to_remove = []
        for ws in list(self.active):
            try:
                await ws.send_text(data)
            except Exception:
                to_remove.append(ws)
        for r in to_remove:
            self.disconnect(r)

manager = ConnectionManager()
events = {}

class RawLog(BaseModel):
    raw: str

@app.post("/ingest")
async def ingest_log(payload: RawLog):
    raw = payload.raw
    import re
    m = re.search(r'\b(\d{3})\b', raw)
    status = int(m.group(1)) if m else 0

    level = "info"
    if status >= 500:
        level = "error"
    elif status >= 400:
        level = "warning"

    event_id = str(uuid.uuid4())
    event = {
        "id": event_id,
        "raw": raw,
        "status": status,
        "level": level,
        "acknowledged": False,
        "timestamp": __import__("time").time()
    }
    events[event_id] = event
    await manager.broadcast({"type": "log_event", "event": event})
    return {"ok": True, "id": event_id}

@app.post("/acknowledge/{event_id}")
async def acknowledge(event_id: str):
    if event_id not in events:
        return {"ok": False, "error": "not_found"}
    events[event_id]["acknowledged"] = True
    await manager.broadcast({"type": "ack", "id": event_id})
    return {"ok": True}

@app.get("/events")
async def list_events():
    return {"events": list(events.values())}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        await ws.send_text(json.dumps({"type": "init", "events": list(events.values())}))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
