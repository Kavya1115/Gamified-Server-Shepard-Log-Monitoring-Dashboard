# agent/agent.py
import time
import requests
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TailHandler(FileSystemEventHandler):
    def __init__(self, path, backend_url):
        self.path = path
        self.backend = backend_url
        self.f = open(path, "r", encoding="utf-8", errors="ignore")
        self.f.seek(0, 2)

    def on_modified(self, event):
        if event.src_path != self.path:
            return
        while True:
            line = self.f.readline()
            if not line:
                break
            self.send_line(line.rstrip("\n"))

    def send_line(self, line):
        try:
            r = requests.post(f"{self.backend}/ingest", json={"raw": line}, timeout=5)
            if r.ok:
                print("sent:", line)
            else:
                print("backend error", r.text)
        except Exception as e:
            print("send failed:", e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to log file to tail")
    parser.add_argument("--backend", default="http://localhost:8000", help="Backend URL")
    args = parser.parse_args()

    handler = TailHandler(args.file, args.backend)
    observer = Observer()
    import os
    observer.schedule(handler, os.path.dirname(args.file) or ".", recursive=False)
    observer.start()
    print("Watching", args.file, "->", args.backend)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
