import threading
import queue
from core.protocol import serialize

class TXThread(threading.Thread):
    def __init__(self, client, tx_queue, stop_event):
        super().__init__(daemon=True)
        self.client     = client
        self.tx_queue   = tx_queue
        self.stop_event = stop_event

    # runs on thread creation
    def run(self):
        while not self.stop_event.is_set():
            try:
                msg  = self.tx_queue.get(timeout=0.1)
                data = serialize(msg)
                self.client.send(data)
            except queue.Empty:
                continue
            except Exception:
                break