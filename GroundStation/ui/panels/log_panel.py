import tkinter as tk
import time
import threading
import queue
from ui.theme import Theme
Theme = Theme()

# Map logging levels to colors (matching both old and new level names)
LEVEL_COLORS = {
    "INFO": "white",
    "DEBUG": "white",
    "WARN": "#f0a500",
    "WARNING": "#f0a500",
    "ERROR": "#cc0000",
    "FAULT": "#ff6600",
    "CRITICAL": "#cc0000"
}

class LogPanel(tk.Frame):
    def __init__(self, parent, log_queue=None):
        super().__init__(parent,highlightbackground=Theme.PANEL_EDGE,highlightcolor=Theme.PANEL_EDGE,highlightthickness=3)
        self._text = tk.Text(self, height=6, state="disabled", wrap="word")
        scroll = tk.Scrollbar(self, command=self._text.yview)
        self._text.config(yscrollcommand=scroll.set)
        self._text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for level, color in LEVEL_COLORS.items():
            self._text.tag_config(level, foreground=color)

        tk.Button(self, text="Clear", command=self._clear).pack(pady=2)

        # Consumer thread for logging queue
        self.log_queue = log_queue if log_queue else queue.Queue()
        self.running = True
        self.consumer_thread = threading.Thread(target=self._consume_logs, daemon=True)
        self.consumer_thread.start()

    def _consume_logs(self):
        """Background thread that reads from log_queue and displays messages."""
        while self.running:
            try:
                msg, level = self.log_queue.get(timeout=0.1)
                self.log(msg, level)
            except queue.Empty:
                pass
            except Exception:
                # Fail silently to avoid crashing logging thread
                pass

    def log(self, msg: str, level: str = "INFO"):
        ts   = time.strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}\n"
        self._text.config(state="normal")
        if int(self._text.index("end-1c").split(".")[0]) > 1000:
            self._text.delete("1.0", "200.0")  # trim oldest lines
        self._text.insert("end", line, level)
        self._text.see("end")
        self._text.config(state="disabled")

    def _clear(self):
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.config(state="disabled")

    def stop(self):
        """Stop the consumer thread."""
        self.running = False