"""
SOL Live Dashboard Web Server
=============================
Receives OpenTelemetry spans and metrics, buffers them, and streams them
via WebSockets to the web dashboard client. Serves the web dashboard UI.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add sol-core to path to enable standalone engine execution
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools" / "sol-core"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sol.dashboard_server")

app = FastAPI(title="SOL Live Manifold Telemetry Dashboard")

# Static directory path
STATIC_DIR = Path(__file__).resolve().parent

# Global buffers
SPANS_BUFFER: list[dict] = []
METRICS_HISTORY: dict[str, list[dict]] = {}
MAX_BUFFER_SIZE = 2000

# Standalone simulation variables
standalone_engine = None
standalone_task = None
standalone_active = False

def get_standalone_engine():
    global standalone_engine
    if standalone_engine is None:
        try:
            from sol_engine import SOLEngine
            import telemetry
            # Force enable telemetry for standalone
            os.environ["SOL_TELEMETRY_ENABLED"] = "true"
            telemetry.init_telemetry("sol-standalone")
            standalone_engine = SOLEngine.from_default_graph()
            logger.info("Standalone SOLEngine loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize standalone engine: {e}")
    return standalone_engine

async def standalone_simulation_loop():
    logger.info("Standalone simulation loop started.")
    engine = get_standalone_engine()
    if not engine:
        logger.error("Could not run standalone loop: engine not initialized.")
        return
    
    try:
        while True:
            # Tick the engine
            engine.step()
            # 5Hz ticks
            await asyncio.sleep(0.2)
    except asyncio.CancelledError:
        logger.info("Standalone simulation loop cancelled.")
    except Exception as e:
        logger.error(f"Error in standalone simulation loop: {e}")


# WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Seed the new connection with existing buffers
        try:
            await websocket.send_json({
                "type": "init",
                "spans": SPANS_BUFFER,
                "metrics": METRICS_HISTORY
            })
        except Exception as e:
            logger.error(f"Error seeding WebSocket connection: {e}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Disconnects will be cleaned up by the WebSocket loop
                pass

manager = ConnectionManager()

# Data models
class TelemetryPayload(BaseModel):
    spans: list[dict] = []
    metrics: list[dict] = []

class InjectRequest(BaseModel):
    label: str
    amount: float

@app.post("/api/telemetry")
async def receive_telemetry(payload: TelemetryPayload):
    # Process spans
    new_spans = []
    for span in payload.spans:
        # Buffer span
        SPANS_BUFFER.append(span)
        if len(SPANS_BUFFER) > MAX_BUFFER_SIZE:
            SPANS_BUFFER.pop(0)
        new_spans.append(span)
    
    # Process metrics
    new_metrics = []
    for metric in payload.metrics:
        name = metric["name"]
        if name not in METRICS_HISTORY:
            METRICS_HISTORY[name] = []
        
        # Buffer metrics points
        for pt in metric.get("data_points", []):
            pt_data = {
                "time": pt.get("time_unix_nano", 0) / 1e9,
                "value": pt.get("value", 0.0),
                "attributes": pt.get("attributes", {})
            }
            METRICS_HISTORY[name].append(pt_data)
            if len(METRICS_HISTORY[name]) > MAX_BUFFER_SIZE:
                METRICS_HISTORY[name].pop(0)
            new_metrics.append({"name": name, "point": pt_data})

    # Broadcast to WebSockets
    if new_spans or new_metrics:
        await manager.broadcast({
            "type": "telemetry",
            "spans": new_spans,
            "metrics": new_metrics
        })

    return {"status": "ok"}


@app.post("/api/inject")
async def trigger_inject(req: InjectRequest):
    global standalone_active, standalone_task
    
    engine = get_standalone_engine()
    if not engine:
        return {"status": "error", "message": "Failed to get engine"}
        
    success = engine.inject(req.label, req.amount)
    logger.info(f"Injecting {req.amount} to '{req.label}' -> success: {success}")
    
    # Start the simulation loop if it's not already running
    if not standalone_active:
        standalone_active = True
        standalone_task = asyncio.create_task(standalone_simulation_loop())
        
    return {"status": "ok", "success": success}


@app.get("/")
async def get_dashboard():
    dashboard_file = STATIC_DIR / "dashboard.html"
    if not dashboard_file.exists():
        return HTMLResponse("<h1>SOL Dashboard File Not Found</h1><p>Ensure dashboard.html is created.</p>", status_code=404)
    return FileResponse(dashboard_file)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for any client messages
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception as e:
                logger.error(f"Error parsing websocket message: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def main():
    parser = argparse.ArgumentParser(description="SOL Live Telemetry Dashboard Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()

    # Create static files if they don't exist
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting SOL Dashboard server at http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
