#!/usr/bin/env python3
"""
Simple Log Agent for Server Shepherd
Monitors log files using polling instead of watchdog to avoid threading issues.
"""

import socket
import time
import json
import sys
from pathlib import Path

class SimpleLogAgent:
    """Simple log agent that polls file for changes."""
    
    def __init__(self, log_file_path: str, backend_host: str = 'localhost', backend_port: int = 9999):
        self.log_file_path: Path = Path(log_file_path)
        self.backend_host: str = backend_host
        self.backend_port: int = backend_port
        self.socket: socket.socket | None = None
        self.last_position: int = 0
        self.connect_to_backend()
        
    def connect_to_backend(self):
        """Establish connection to the backend server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.backend_host, self.backend_port))
            print(f"Connected to backend at {self.backend_host}:{self.backend_port}")
        except ConnectionRefusedError:
            print(f"Failed to connect to backend at {self.backend_host}:{self.backend_port}")
            print("Make sure the backend server is running first!")
            sys.exit(1)
        except Exception as e:
            print(f"Error connecting to backend: {e}")
            sys.exit(1)
    
    def send_log_line(self, line: str) -> None:
        """Send a log line to the backend."""
        try:
            log_data: dict[str, object] = {
                "timestamp": time.time(),
                "raw_line": line,
                "source": str(self.log_file_path)
            }
            
            message: str = json.dumps(log_data) + '\n'
            if self.socket is not None:
                self.socket.send(message.encode('utf-8'))
                print(f"Sent log line: {line[:50]}...")
            else:
                print("Socket is not connected. Cannot send log line.")
            
        except Exception as e:
            print(f"Error sending log line: {e}")
            # Try to reconnect
            try:
                if self.socket is not None:
                    self.socket.close()
            except Exception:
                pass
            self.connect_to_backend()
    
    def monitor_file(self):
        """Monitor the log file for new lines."""
        print(f"Monitoring file: {self.log_file_path}")
        print("Press Ctrl+C to stop.")
        
        try:
            while True:
                if self.log_file_path.exists():
                    with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # Move to last known position
                        f.seek(self.last_position)
                        
                        # Read new lines
                        new_lines = f.readlines()
                        self.last_position = f.tell()
                        
                        # Send new lines
                        for line in new_lines:
                            line = line.strip()
                            if line:  # Only send non-empty lines
                                self.send_log_line(line)
                else:
                    print(f"Log file {self.log_file_path} not found, waiting...")
                
                time.sleep(0.5)  # Poll every 500ms
                
        except KeyboardInterrupt:
            print("\nStopping log agent...")
        except Exception as e:
            print(f"Error monitoring file: {e}")
        finally:
            if self.socket:
                self.socket.close()
            print("Log agent stopped.")

def main():
    """Main function to start the log agent."""
    if len(sys.argv) < 2:
        print("Usage: python simple_log_agent.py <log_file_path> [backend_host] [backend_port]")
        print("Example: python simple_log_agent.py logs/sample.log localhost 9999")
        sys.exit(1)
    
    log_file_path = sys.argv[1]
    backend_host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
    backend_port = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
    
    # Check if log file exists
    if not Path(log_file_path).exists():
        print(f"Error: Log file '{log_file_path}' does not exist!")
        sys.exit(1)
    
    print(f"Starting simple log agent for: {log_file_path}")
    print(f"Backend: {backend_host}:{backend_port}")
    
    # Create and start agent
    agent = SimpleLogAgent(log_file_path, backend_host, backend_port)
    agent.monitor_file()

if __name__ == "__main__":
    main()
