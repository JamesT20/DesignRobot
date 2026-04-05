import tkinter as tk
from tkinter import ttk
import threading
import requests
import json
from PIL import Image, ImageTk
import io

SERVER = "http://192.168.4.1"

class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Telemetry Dashboard")
        self.configure(bg="#1a1a2e")
        self._build_ui()
        self._running = True
        # Start both background threads
        threading.Thread(target=self._poll_telemetry, daemon=True).start()
        threading.Thread(target=self._stream_video, daemon=True).start()

    def _build_ui(self):
        # Video label
        self.video_label = tk.Label(self, bg="black")
        self.video_label.pack(pady=10)

        # Telemetry frame
        tlm_frame = tk.Frame(self, bg="#1a1a2e")
        tlm_frame.pack(fill="x", padx=20)
        self.tlm_vars = {}   # will hold StringVar per field

    # ── Telemetry ──────────────────────────────────────────────────────────────

    def _poll_telemetry(self):
        """Runs in a background thread; fetches /tlm every 200 ms."""
        while self._running:
            try:
                resp = requests.get(f"{SERVER}/tlm", timeout=2)
                data = resp.json()          # dict of telemetry values
                self.after(0, self._update_telemetry, data)
            except Exception as e:
                print(f"[tlm] {e}")
            threading.Event().wait(0.2)     # 200 ms poll interval

    def _update_telemetry(self, data: dict):
        """Called on the main thread — safe to touch widgets."""
        for key, value in data.items():
            if key not in self.tlm_vars:
                # Dynamically create a row for each new key
                var = tk.StringVar()
                self.tlm_vars[key] = var
                row = tk.Frame(self, bg="#1a1a2e")
                row.pack(fill="x", padx=20, pady=2)
                tk.Label(row, text=key, width=20, anchor="w",
                         bg="#1a1a2e", fg="#888", font=("Courier", 10)).pack(side="left")
                tk.Label(row, textvariable=var, anchor="w",
                         bg="#1a1a2e", fg="#00ff88", font=("Courier", 10, "bold")).pack(side="left")
            self.tlm_vars[key].set(str(value))

    # ── MJPEG stream ───────────────────────────────────────────────────────────

    def _stream_video(self):
        """Runs in a background thread; parses the multipart MJPEG stream."""
        try:
            with requests.get(f"{SERVER}/stream", stream=True, timeout=10) as resp:
                buf = b""
                for chunk in resp.iter_content(chunk_size=4096):
                    if not self._running:
                        break
                    buf += chunk
                    # JPEG frames start with FF D8 and end with FF D9
                    start = buf.find(b"\xff\xd8")
                    end   = buf.find(b"\xff\xd9")
                    if start != -1 and end != -1 and end > start:
                        jpg = buf[start:end + 2]
                        buf = buf[end + 2:]
                        self.after(0, self._update_frame, jpg)
        except Exception as e:
            print(f"[stream] {e}")

    def _update_frame(self, jpg_bytes: bytes):
        """Called on the main thread — converts JPEG bytes → PhotoImage."""
        try:
            img = Image.open(io.BytesIO(jpg_bytes))
            photo = ImageTk.PhotoImage(img)
            self.video_label.configure(image=photo)
            self.video_label.image = photo   # keep reference alive
        except Exception as e:
            print(f"[frame] {e}")

    def destroy(self):
        self._running = False
        super().destroy()

if __name__ == "__main__":
    app = Dashboard()
    app.mainloop()