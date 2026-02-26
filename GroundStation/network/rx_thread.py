import threading
from core.protocol import deserialize, is_valid

class RXThread(threading.Thread):
    def __init__(self, client, rx_queue, stop_event):
        super().__init__(daemon=True)
        self.client     = client
        self.rx_queue   = rx_queue
        self.stop_event = stop_event

    # runs on thread creation
    def run(self):
        while not self.stop_event.is_set():
            try:
                line = self.client.receive_line()
                msg  = deserialize(line)
                if msg and is_valid(msg):
                    if not self.rx_queue.full():
                        self.rx_queue.put(msg)
            except Exception:
                break  # socket died — connection manager will handle reconnect