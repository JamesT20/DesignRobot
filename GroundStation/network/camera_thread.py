import threading
import time
import requests
from config import HOST

class CameraThread(threading.Thread):
    def __init__(self, frame_queue, stop_event):
        super().__init__(daemon=True)
        self.frame_queue    = frame_queue
        self.stop_event     = stop_event

        
    def run(self):
        while not self.stop_event.is_set():
            try:
                resp = requests.get(f"http://{HOST}/stream", timeout=10)
                data = resp.content
                start = data.find(b"\xff\xd8")
                end   = data.find(b"\xff\xd9", start)
                if start != -1 and end != -1:
                    self.frame_queue.put(data[start:end + 2])
                time.sleep(0.1)
            except Exception as e:
                pass