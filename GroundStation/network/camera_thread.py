import threading
from config import HOST

class CameraThread(threading.Thread):
    def __init__(self, session, frame_queue, stop_event):
        super().__init__(daemon=True)
        self.session         = session
        self.frame_queue    = frame_queue
        self.stop_event     = stop_event

        
    def run(self):
        while not self.stop_event.is_set():
            try:
                with self.session.get(f"{HOST}/stream", stream=True, timeout=10) as resp:
                    buf = b""
                    for chunk in resp.iter_content(chunk_size=16384):
                        if not self._running:
                            return
                        buf += chunk
                        while True:
                            start = buf.find(b"\xff\xd8")
                            end   = buf.find(b"\xff\xd9", start)
                            if start == -1 or end == -1:
                                break
                            jpg = buf[start:end + 2]
                            buf = buf[end + 2:]
                            self.rx_queue.put(jpg)
            except Exception:
                pass