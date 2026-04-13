import threading
import time
import re
import json
import requests
from config import HOST
from core.logger import get_logger

logger = get_logger("network.rx_thread")

# Matches bare nan/inf/-inf values (case-insensitive, firmware may vary)
_NAN_RE = re.compile(r':\s*(nan|-?inf)\b', re.IGNORECASE)

def _parse_telemetry(text: str) -> dict:
    """Parse firmware JSON that may contain bare nan/inf literals."""
    sanitized = _NAN_RE.sub(': null', text)
    return json.loads(sanitized)

class RXThread(threading.Thread):
    def __init__(self, rx_queue, stop_event):
        super().__init__(daemon=True)
        self.rx_queue   = rx_queue
        self.stop_event = stop_event

    def run(self):
        logger.info("RX thread started")
        while not self.stop_event.is_set():
            try:
                resp = requests.get(f"http://{HOST}/tlm", timeout=1)
                try:
                    data = _parse_telemetry(resp.text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse telemetry (char {e.pos}): {resp.text!r}")
                    time.sleep(0.2)
                    continue
                self.rx_queue.put(data)
                time.sleep(0.2)

            except requests.exceptions.Timeout:
                logger.warning("Telemetry request timeout")
                time.sleep(0.5)   # back off on timeout
            except requests.exceptions.ConnectionError:
                logger.warning("Telemetry connection lost - retrying in 1s")
                time.sleep(1.0)   # back off heavily on connection drop
            except Exception as e:
                logger.error(f"Unexpected error in RX thread: {e}", exc_info=True)
                time.sleep(0.5)

        logger.info("RX thread stopped")