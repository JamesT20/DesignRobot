import threading
import queue
import requests
from core.logger import get_logger

logger = get_logger("network.tx_thread")

# Transmit thread — reads tx_queue, sends command sequences to ESP32 via HTTP POST
class TXThread(threading.Thread):

    BASE_URL = "http://192.168.4.1"  # ESP32 AP default IP

    def __init__(self, tx_queue: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.tx_queue   = tx_queue
        self.stop_event = stop_event
        self.session    = requests.Session()
        self.session.headers.update({"Connection": "close"})  # ESP32 keep-alive bug

    def run(self):
        logger.info("TX thread started")
        while not self.stop_event.is_set():
            try:
                msg = self.tx_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self._dispatch(msg)
            except requests.exceptions.Timeout:
                logger.error("Command submission timeout - ESP32 unreachable")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error during command transmission: {e}")
            except requests.RequestException as e:
                logger.error(f"HTTP error sending command: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in TX thread: {e}", exc_info=True)
        logger.info("TX thread stopped")

    def _dispatch(self, msg: dict):
        """Route a message to the correct ESP32 endpoint."""
        endpoint = msg.get("endpoint", "/cmd")

        if endpoint == "/cmd/stop":
            logger.info("Sending emergency stop command")
            resp = self.session.post(
                f"{self.BASE_URL}/cmd/stop",
                timeout=3
            )

        elif endpoint == "/cmd":
            commands = msg.get("commands", [])
            cmd_names = [c.get("cmd", "?") for c in commands]
            logger.info(f"Sending {len(commands)} command(s): {cmd_names}")
            resp = self.session.post(
                f"{self.BASE_URL}/cmd",
                json=commands,
                timeout=5
            )

        else:
            logger.error(f"Unknown endpoint: {endpoint}")
            return
        
        if resp.status_code == 400:
            try:
                err = resp.json().get("error", "")
            except Exception:
                err = ""
            if err == "empty body":
                logger.debug("ESP32 returned 'empty body' — ignoring, command will still execute")
                return

        if not resp.ok:
            logger.error(f"Command rejected ({resp.status_code}): {resp.text}")
            logger.error(f"Request headers: {resp.request.headers}")
        resp.raise_for_status()
        logger.debug(f"Command response: {resp.status_code} {resp.text}")