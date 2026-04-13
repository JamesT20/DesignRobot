import threading
import time
import requests
from config import HOST
from core.logger import get_logger

logger = get_logger("network.camera_thread")

class CameraThread(threading.Thread):
    def __init__(self, frame_queue, stop_event):
        super().__init__(daemon=True)
        self.frame_queue    = frame_queue
        self.stop_event     = stop_event

        
    def run(self):
        logger.info("Camera thread started")
        error_count = 0
        while not self.stop_event.is_set():
            try:
                resp = requests.get(f"http://{HOST}/stream", timeout=10)
                data = resp.content
                start = data.find(b"\xff\xd8")
                end   = data.find(b"\xff\xd9", start)
                if start != -1 and end != -1:
                    self.frame_queue.put(data[start:end + 2])
                    error_count = 0  # reset error counter on successful frame
                time.sleep(0.1)
            except requests.exceptions.Timeout:
                error_count += 1
                if error_count % 10 == 0:  # log every 10th timeout
                    logger.warning(f"Camera stream timeout (attempt {error_count})")
            except requests.exceptions.ConnectionError as e:
                error_count += 1
                if error_count == 1:
                    logger.error(f"Camera connection error: {e}")
            except Exception as e:
                logger.error(f"Error in camera thread: {e}", exc_info=True)
        logger.info("Camera thread stopped")