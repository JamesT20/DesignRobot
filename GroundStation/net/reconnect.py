import time
from config import RECONNECT_INTERVAL, MAX_RECONNECT_ATTEMPTS

# manages recinnecting
class ReconnectManager:
    def __init__(self, client, on_status):
        self.client = client
        self.on_status = on_status  # callback(status: str)

    # used to attempt reconnect
    def connect_with_retry(self):
        for attempt in range(MAX_RECONNECT_ATTEMPTS):
            try:
                self.client.connect()
                self.on_status("connected")
                return True
            except OSError:
                self.on_status(f"retrying ({attempt + 1})")
                time.sleep(RECONNECT_INTERVAL * (1 + attempt * 0.5))  # backoff
        self.on_status("failed")
        return False