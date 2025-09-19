import time
import socket
import sys
import argparse
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LogFileHandler(FileSystemEventHandler):
    def __init__(self, log_file_path, tcp_host, tcp_port):
        self.log_file_path = Path(log_file_path)
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.file_position = 0
        self.socket = None
        
        # Initialize file position to end of file
        if self.log_file_path.exists():
            with open(self.log_file_path, 'rb') as f:
                f.seek(0, 2)  # Seek to end of file
                self.file_position = f.tell()
        
        self.connect_to_server()
    
    def connect_to_server(self):
        """Establish TCP connection to the central server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.tcp_host, self.tcp_port))
            logger.info(f"Connected to server at {self.tcp_host}:{self.tcp_port}")
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            self.socket = None
    
    def send_log_line(self, line):
        """Send a log line to the central server"""
        if not self.socket:
            self.connect_to_server()
        
        if self.socket:
            try:
                self.socket.send(line.encode('utf-8') + b'\n')
                logger.debug(f"Sent log line: {line.strip()}")
            except Exception as e:
                logger.error(f"Failed to send log line: {e}")
                self.socket = None
    
    def read_new_lines(self):
        """Read new lines from the log file"""
        if not self.log_file_path.exists():
            return
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                f.seek(self.file_position)
                new_lines = f.readlines()
                self.file_position = f.tell()
                
                for line in new_lines:
                    line = line.strip()
                    if line:
                        self.send_log_line(line)
                        
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        if Path(event.src_path) == self.log_file_path:
            logger.debug(f"Log file modified: {event.src_path}")
            self.read_new_lines()
    
    def close(self):
        """Close the TCP connection"""
        if self.socket:
            self.socket.close()
            logger.info("Disconnected from server")

def generate_sample_logs(log_file_path):
    """Generate sample NGINX log entries for testing"""
    import random
    import datetime
    
    sample_ips = [
        "192.168.1.101", "10.0.0.55", "203.45.67.89", 
        "172.16.0.99", "192.168.1.50", "10.10.10.1"
    ]
    
    sample_urls = [
        "/api/users", "/api/orders", "/dashboard", "/login", 
        "/api/products", "/old-page", "/api/auth", "/static/app.js"
    ]
    
    methods = ["GET", "POST", "PUT", "DELETE"]
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    ]
    
    with open(log_file_path, 'a') as f:
        while True:
            # Generate log entry
            ip = random.choice(sample_ips)
            timestamp = datetime.datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")
            method = random.choice(methods)
            url = random.choice(sample_urls)
            
            # Status code distribution: 80% success, 15% client errors, 5% server errors
            rand = random.random()
            if rand < 0.80:
                status = random.choice([200, 201, 204])
            elif rand < 0.95:
                status = random.choice([400, 401, 403, 404])
            else:
                status = random.choice([500, 502, 503])
            
            size = random.randint(100, 10000)
            user_agent = random.choice(user_agents)
            response_time = round(random.uniform(0.1, 5.0), 3)
            
            log_line = f'{ip} - - [{timestamp}] "{method} {url} HTTP/1.1" {status} {size} "-" "{user_agent}" {response_time}\n'
            
            f.write(log_line)
            f.flush()
            
            logger.info(f"Generated log: {method} {url} -> {status}")
            
            # Wait 2-8 seconds between log entries
            time.sleep(random.uniform(2, 8))

def main():
    parser = argparse.ArgumentParser(description='Log monitoring agent for Server Shepherd')
    parser.add_argument('--log-file', required=True, help='Path to the log file to monitor')
    parser.add_argument('--server-host', default='localhost', help='Server host (default: localhost)')
    parser.add_argument('--server-port', type=int, default=9999, help='Server port (default: 9999)')
    parser.add_argument('--generate-logs', action='store_true', help='Generate sample logs instead of monitoring')
    
    args = parser.parse_args()
    
    log_file_path = Path(args.log_file)
    
    if args.generate_logs:
        logger.info(f"Generating sample logs to {log_file_path}")
        # Create log directory if it doesn't exist
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            generate_sample_logs(log_file_path)
        except KeyboardInterrupt:
            logger.info("Log generation stopped")
        return
    
    if not log_file_path.exists():
        logger.error(f"Log file does not exist: {log_file_path}")
        sys.exit(1)
    
    # Create event handler and observer
    event_handler = LogFileHandler(log_file_path, args.server_host, args.server_port)
    observer = Observer()
    observer.schedule(event_handler, str(log_file_path.parent), recursive=False)
    
    # Start monitoring
    observer.start()
    logger.info(f"Monitoring log file: {log_file_path}")
    logger.info(f"Sending to server: {args.server_host}:{args.server_port}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping log monitoring...")
        observer.stop()
        event_handler.close()
    
    observer.join()

if __name__ == "__main__":
    main()