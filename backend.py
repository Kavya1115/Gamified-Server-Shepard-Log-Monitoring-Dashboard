#!/usr/bin/env python3
"""
Server Shepherd Backend
FastAPI server that receives log data via TCP and broadcasts it via WebSocket.
"""

import asyncio
import json
import socket
import threading
import time
from contextlib import asynccontextmanager
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Global variables for managing connections and data
active_connections: List[WebSocket] = []
log_buffer: List[Dict[str, Any]] = []
tcp_server = None
tcp_thread = None
main_event_loop: asyncio.AbstractEventLoop | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global tcp_thread, main_event_loop
    # Capture the running event loop for thread-safe WS broadcasting
    try:
        main_event_loop = asyncio.get_running_loop()
    except RuntimeError:
        main_event_loop = None
    tcp_thread = threading.Thread(target=start_tcp_server)
    tcp_thread.daemon = True
    tcp_thread.start()
    print("TCP server started on port 9999")
    yield
    # Shutdown
    if tcp_server:
        tcp_server.close()

app = FastAPI(title="Server Shepherd Backend", version="1.0.0", lifespan=lifespan)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for managing connections and data
active_connections: List[WebSocket] = []
log_buffer: List[Dict[str, Any]] = []
tcp_server = None
tcp_thread = None

class LogData(BaseModel):
    timestamp: float
    raw_line: str
    source: str
    parsed_data: Dict[str, Any] = {}

class AcknowledgeRequest(BaseModel):
    log_id: str
    timestamp: float

def parse_nginx_log(log_line: str) -> Dict[str, Any]:
    """
    Parse NGINX access log line into structured data.
    Format: IP - - [timestamp] "method path protocol" status size "referer" "user_agent"
    """
    try:
        # Handle empty or malformed lines
        if not log_line or not log_line.strip():
            return {"status_code": 500, "ip": "unknown", "method": "UNKNOWN", "path": "/", "size": 0, "user_agent": "unknown"}
        
        parts = log_line.split('"')
        if len(parts) < 3:
            # Try to extract basic info even from malformed logs
            words = log_line.split()
            if len(words) >= 1:
                return {
                    "status_code": 500, 
                    "ip": words[0] if words else "unknown", 
                    "method": "UNKNOWN", 
                    "path": "/", 
                    "size": 0, 
                    "user_agent": "unknown"
                }
            return {"status_code": 500, "ip": "unknown", "method": "UNKNOWN", "path": "/", "size": 0, "user_agent": "unknown"}
        
        # Extract IP and timestamp
        ip_part = parts[0].strip()
        ip = ip_part.split()[0] if ip_part else "unknown"
        
        # Extract request details
        request_part = parts[1]
        request_parts = request_part.split()
        method = request_parts[0] if len(request_parts) > 0 else "UNKNOWN"
        path = request_parts[1] if len(request_parts) > 1 else "/"
        
        # Extract status code and size
        status_size_part = parts[2].strip().split()
        status_code = 500
        size = 0
        
        if status_size_part:
            try:
                status_code = int(status_size_part[0])
            except (ValueError, IndexError):
                status_code = 500
                
        if len(status_size_part) > 1:
            try:
                size = int(status_size_part[1])
            except (ValueError, IndexError):
                size = 0
        
        return {
            "status_code": status_code,
            "ip": ip,
            "method": method,
            "path": path,
            "size": size,
            "user_agent": parts[3] if len(parts) > 3 else "unknown"
        }
    except Exception as e:
        print(f"Error parsing log line: {e}")
        return {"status_code": 500, "ip": "unknown", "method": "UNKNOWN", "path": "/", "size": 0, "user_agent": "unknown"}

async def broadcast_log_data(log_data: Dict[str, Any]):
    """Broadcast log data to all connected WebSocket clients."""
    if active_connections:
        message = json.dumps(log_data)
        disconnected = []
        
        for connection in active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            active_connections.remove(connection)

def handle_tcp_connection(client_socket: socket.socket, address: tuple[str, int]) -> None:
    """Handle incoming TCP connections from log agents."""
    print(f"TCP connection from {address}")
    
    try:
        while True:
            data: bytes = client_socket.recv(4096)
            if not data:
                break
            
            # Decode and process each line
            lines: list[str] = data.decode('utf-8').strip().split('\n')
            for line in lines:
                if line.strip():
                    try:
                        log_data: Dict[str, Any] = json.loads(line)
                        
                        # Parse the raw log line
                        parsed_data: Dict[str, Any] = parse_nginx_log(log_data["raw_line"])
                        log_data["parsed_data"] = parsed_data
                        log_data["id"] = f"{int(time.time() * 1000)}_{hash(line) % 10000}"
                        
                        # Add to buffer (keep last 1000 entries)
                        log_buffer.append(log_data)
                        if len(log_buffer) > 1000:
                            log_buffer.pop(0)
                        
                        # Broadcast to WebSocket clients using the main event loop captured at startup
                        try:
                            if main_event_loop and not main_event_loop.is_closed():
                                asyncio.run_coroutine_threadsafe(
                                    broadcast_log_data(log_data), main_event_loop
                                )
                            else:
                                # No loop captured; skip broadcast safely
                                pass
                        except Exception as e:
                            print(f"Error broadcasting log data: {e}")
                        
                        print(f"Processed log: {parsed_data['status_code']} {parsed_data['method']} {parsed_data['path']}")
                        
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")
                    except Exception as e:
                        print(f"Error processing log data: {e}")
    
    except Exception as e:
        print(f"Error in TCP connection: {e}")
    finally:
        client_socket.close()
        print(f"TCP connection closed: {address}")

def start_tcp_server():
    """Start TCP server in a separate thread."""
    global tcp_server
    
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_server.bind(('0.0.0.0', 9999))
    tcp_server.listen(5)
    
    print("TCP server started on port 9999")
    
    while True:
        try:
            client_socket, address = tcp_server.accept()
            # Handle each connection in a separate thread
            client_thread = threading.Thread(
                target=handle_tcp_connection,
                args=(client_socket, address)
            )
            client_thread.daemon = True
            client_thread.start()
        except Exception as e:
            print(f"Error accepting TCP connection: {e}")
            break


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time log data."""
    await websocket.accept()
    active_connections.append(websocket)
    print(f"WebSocket client connected. Total connections: {len(active_connections)}")
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"WebSocket client disconnected. Total connections: {len(active_connections)}")

@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with basic info."""
    return {
        "message": "Server Shepherd Backend",
        "version": "1.0.0",
        "active_connections": len(active_connections),
        "log_buffer_size": len(log_buffer)
    }

@app.get("/logs")
async def get_recent_logs(limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
    """Get recent log entries."""
    return {"logs": log_buffer[-limit:]}

@app.post("/acknowledge")
async def acknowledge_error(request: AcknowledgeRequest) -> Dict[str, Any]:
    """Acknowledge an error log entry."""
    # Find the log entry in the buffer and mark it as acknowledged
    for log in log_buffer:
        if log.get("id") == request.log_id:
            log["acknowledged"] = True
            log["acknowledged_at"] = time.time()
            return {"status": "acknowledged", "log_id": request.log_id}
    
    return {"status": "not_found", "log_id": request.log_id, "message": "Log entry not found"}

@app.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Get basic statistics about the logs."""
    if not log_buffer:
        return {"total_logs": 0, "error_count": 0, "success_count": 0, "error_rate": 0.0}
    
    error_count = sum(1 for log in log_buffer if log.get("parsed_data", {}).get("status_code", 200) >= 400)
    success_count = len(log_buffer) - error_count
    error_rate = error_count / len(log_buffer) if log_buffer else 0.0
    
    return {
        "total_logs": len(log_buffer),
        "error_count": error_count,
        "success_count": success_count,
        "error_rate": error_rate
    }

if __name__ == "__main__":
    print("Starting Server Shepherd Backend...")
    print("TCP server will listen on port 9999")
    print("WebSocket server will be available at ws://localhost:8000/ws")
    print("API documentation at http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
