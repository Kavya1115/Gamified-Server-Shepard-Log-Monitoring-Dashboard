#!/usr/bin/env python3
"""
Server Shepherd Log Agent
Monitors log files using watchdog and sends new log lines via TCP to the backend.
"""

import socket
import time
import json
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class LogFileHandler(FileSystemEventHandler):
    """Handles file modification events for log monitoring."""
    
    def __init__(self, log_file_path: str, backend_host: str = 'localhost', backend_port: int = 9999) -> None:
        self.log_file_path: Path = Path(log_file_path)
        self.backend_host: str = backend_host
        self.backend_port: int = backend_port
        self.socket: socket.socket | None = None
        self.last_line_count: int = 0
        self.connect_to_backend()
        
    def connect_to_backend(self) -> None:
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
    
    def on_modified(self, event: FileSystemEventHandler) -> None:
        """Handle file modification events."""
        if getattr(event, "is_directory", False):
            return
            
        # Check if the modified file is our target log file
        if Path(getattr(event, "src_path", "")) == self.log_file_path:
            self.send_new_log_lines()
    
    def send_new_log_lines(self) -> None:
        """Read new lines from the log file and send them to backend."""
        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read all lines and get the new ones
                lines: list[str] = f.readlines()
                new_lines: list[str] = lines[self.last_line_count:] if hasattr(self, 'last_line_count') else lines
                self.last_line_count = len(lines)
                
                for line in new_lines:
                    line = line.strip()
                    if line:  # Only send non-empty lines
                        # Send the log line as JSON
                        log_data: dict[str, object] = {
                            "timestamp": time.time(),
                            "raw_line": line,
                            "source": str(self.log_file_path)
                        }
                        
                        message: str = json.dumps(log_data) + '\n'
                        if self.socket is not None:
                            self.socket.send(message.encode('utf-8'))
                        print(f"Sent log line: {line[:50]}...")
                        
        except Exception as e:
            print(f"Error reading/sending log file: {e}")
            # Try to reconnect if connection was lost
            try:
                if self.socket is not None:
                    self.socket.close()
            except Exception:
                pass
            self.connect_to_backend()

def main():
    """Main function to start the log agent."""
    if len(sys.argv) < 2:
        print("Usage: python log_agent.py <log_file_path> [backend_host] [backend_port]")
        print("Example: python log_agent.py /var/log/nginx/access.log localhost 9999")
        sys.exit(1)
    
    log_file_path = sys.argv[1]
    backend_host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
    backend_port = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
    
    # Check if log file exists
    if not Path(log_file_path).exists():
        print(f"Error: Log file '{log_file_path}' does not exist!")
        sys.exit(1)
    
    print(f"Starting log agent for: {log_file_path}")
    print(f"Backend: {backend_host}:{backend_port}")
    
    # Create event handler
    event_handler = LogFileHandler(log_file_path, backend_host, backend_port)
    observer = Observer()
    observer.schedule(event_handler, str(Path(log_file_path).parent), recursive=False)
    
    # Start monitoring
    try:
        observer.start()
        print("Log agent started. Monitoring for changes...")
        print("Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping log agent...")
        observer.stop()
        if event_handler.socket is not None:
            event_handler.socket.close()
    except Exception as e:
        print(f"Error in log agent: {e}")
        observer.stop()
        if event_handler.socket is not None:
            event_handler.socket.close()
    finally:
        observer.join()
        print("Log agent stopped.")
        print("Log agent stopped.")

if __name__ == "__main__":
    main()
