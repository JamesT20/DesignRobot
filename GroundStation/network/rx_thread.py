import threading
from config import HOST
# Receive thread — reads socket, puts messages on rx_queue
class RXThread(threading.Thread):
    def __init__(self, session, rx_queue, stop_event):
        super().__init__(daemon=True)
        self.session    = session
        self.rx_queue   = rx_queue
        self.stop_event = stop_event

    # runs on thread creation
    def run(self):
        while not self.stop_event.is_set():
            try:
                resp = self._session.get(f"{HOST}/tlm", timeout=2)
                data = resp.json()
                self.rx_queue.put(data)
            except Exception:
                break  # socket died — connection manager will handle reconnect