import threading
import time
import requests
from config import HOST
from core.logger import get_logger

logger = get_logger("network.rx_thread")

# Receive thread — reads socket, puts messages on rx_queue
class RXThread(threading.Thread):
    def __init__(self, rx_queue, stop_event):
        super().__init__(daemon=True)
        self.rx_queue   = rx_queue
        self.stop_event = stop_event

    # runs on thread creation
    def run(self):
        logger.info("RX thread started")
        while not self.stop_event.is_set():
            try:
                resp = requests.get(f"http://{HOST}/tlm", timeout=1)
                data = resp.json()
                self.rx_queue.put(data)
                time.sleep(0.2)
            except requests.exceptions.Timeout:
                logger.error("Telemetry request timeout - connection may be lost")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error during telemetry fetch: {e}")
            except Exception as e:
                logger.error(f"Error receiving telemetry: {e}", exc_info=True)
        logger.info("RX thread stopped")
