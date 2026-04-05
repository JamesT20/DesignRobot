import threading
import urllib.request
import urllib.error
import io
import time
from PIL import Image

class CameraThread:
    """
    Connects to a static ESP32 MJPEG stream endpoint and continuously pulls frames.
    URL is set once at construction and never changes.
    Follows the same pattern as ConnectionManager.
    """

    JPEG_SOI        = b'\xff\xd8'
    JPEG_EOI        = b'\xff\xd9'
    CHUNK_SIZE      = 4096
    RETRY_INTERVAL  = 3.0
    CONNECT_TIMEOUT = 5.0

    def __init__(self, frame_queue):
        self.frame_queue = frame_queue
        self.url         = ''

        # Public state — read by UI poll loop
        self.stream_active = False
        self.fps           = 0
        self.frame_count   = 0
        self.error_msg     = ""

        # Internal
        self._stop         = threading.Event()
        self._thread       = None
        self._fps_count    = 0
        self._fps_timer    = time.time()

        # Callback for UI — mirrors on_state_change in ConnectionManager
        self.on_state_change = None

    # ─── Public API ───────────────────────────────────────────────────────────

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._set_active(False)

    def get_status(self) -> dict:
        return {
            "CAM_STREAM_ACTIVE": self.stream_active,
            "CAM_FPS":           self.fps,
            "CAM_FRAME_COUNT":   self.frame_count,
            "CAM_ERROR":         self.error_msg,
        }

    # ─── Stream Loop ──────────────────────────────────────────────────────────

    def _stream_loop(self):
        while not self._stop.is_set():
            self._stream()
            if not self._stop.is_set():
                self._set_active(False)
                self._stop.wait(timeout=self.RETRY_INTERVAL)
        self._set_active(False)

    def _stream(self):
        stream = None
        buffer = b""

        try:
            stream = urllib.request.urlopen(self.url, timeout=self.CONNECT_TIMEOUT)
            self._set_active(True)
            self.error_msg  = ""
            self._fps_count = 0
            self._fps_timer = time.time()

            while not self._stop.is_set():
                try:
                    chunk = stream.read(self.CHUNK_SIZE)
                except Exception as e:
                    self.error_msg = str(e)
                    break

                if not chunk:
                    break

                buffer = self._extract_frames(buffer + chunk)
                self._update_fps()

        except urllib.error.URLError as e:
            self.error_msg = f"Connection failed: {e.reason}"

        except Exception as e:
            self.error_msg = str(e)

        finally:
            self._set_active(False)
            if stream:
                try:
                    stream.close()
                except Exception:
                    pass

    # ─── Frame Extraction ─────────────────────────────────────────────────────

    def _extract_frames(self, buffer: bytes) -> bytes:
        while True:
            start = buffer.find(self.JPEG_SOI)
            if start == -1:
                buffer = b""
                break
            if start > 0:
                buffer = buffer[start:]
            end = buffer.find(self.JPEG_EOI)
            if end == -1:
                break
            jpg    = buffer[:end + 2]
            buffer = buffer[end + 2:]
            self._decode_and_queue(jpg)
        return buffer

    def _decode_and_queue(self, jpg: bytes):
        try:
            img = Image.open(io.BytesIO(jpg))
            img.load()
            if not self.frame_queue.full():
                self.frame_queue.put_nowait(img)
            self._fps_count  += 1
            self.frame_count += 1
        except Exception:
            pass

    # ─── FPS ──────────────────────────────────────────────────────────────────

    def _update_fps(self):
        now = time.time()
        if now - self._fps_timer >= 1.0:
            self.fps        = self._fps_count
            self._fps_count = 0
            self._fps_timer = now

    # ─── State ────────────────────────────────────────────────────────────────

    def _set_active(self, active: bool):
        self.stream_active = active
        if not active:
            self.fps = 0
        if self.on_state_change:
            self.on_state_change(active)