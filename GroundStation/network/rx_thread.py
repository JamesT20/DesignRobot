import threading
import time
import requests
from config import HOST
# Receive thread — reads socket, puts messages on rx_queue
class RXThread(threading.Thread):
    def __init__(self, rx_queue, stop_event):
        super().__init__(daemon=True)
        self.rx_queue   = rx_queue
        self.stop_event = stop_event

    # runs on thread creation
    def run(self):
        while not self.stop_event.is_set():
            try:
                resp = requests.get(f"http://{HOST}/tlm", timeout=1)
                data = resp.json()
                self.rx_queue.put(data)
                time.sleep(0.2)
            except Exception as e:
                print('timeout',e)
