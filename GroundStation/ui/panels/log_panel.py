import tkinter as tk
import time
import threading
import queue
from ui.theme import Theme
Theme = Theme()

# Map logging levels to colors (matching both old and new level names)
LEVEL_COLORS = {
    "INFO": Theme.TEXT,
    "DEBUG": Theme.TEXT,
    "WARN": Theme.WARN_COLOR,
    "WARNING": Theme.WARN_COLOR,
    "ERROR": Theme.ERROR_COLOR,
    "FAULT": Theme.WARN_COLOR,
    "CRITICAL": Theme.ERROR_COLOR
}

class LogPanel(tk.Frame):
    def __init__(self, parent, log_queue=None):
        super().__init__(parent,highlightbackground=Theme.PANEL_EDGE,highlightcolor=Theme.PANEL_EDGE,highlightthickness=3)
        self._filter_var = tk.StringVar(value="ALL")
        filter_frame = tk.Frame(self)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 0))
        tk.Label(filter_frame, text="Filter:").pack(side="left")
        tk.OptionMenu(filter_frame, self._filter_var, "ALL", "DEBUG", "INFO", "WARN", "ERROR").pack(side="left", padx=(4, 0))

        self._text = tk.Text(self, height=10, state="disabled", wrap="word")
        scroll = tk.Scrollbar(self, command=self._text.yview)
        self._text.config(yscrollcommand=scroll.set)

        self._text.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=4)
        scroll.grid(row=1, column=1, sticky="ns", pady=4)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        for level, color in LEVEL_COLORS.items():
            self._text.tag_config(level, foreground=color)

        tk.Button(self, text="Clear", command=self._clear).grid(
            row=2, column=0, columnspan=2, pady=(0, 8))

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
        normalized = level.upper()
        if self._filter_var.get() != "ALL" and self._filter_var.get() != normalized:
            return
        ts   = time.strftime("%H:%M:%S")
        line = f"[{ts}] [{normalized}] {msg}\n"
        self._text.config(state="normal")
        if int(self._text.index("end-1c").split(".")[0]) > 1000:
            self._text.delete("1.0", "200.0")  # trim oldest lines
        self._text.insert("end", line, normalized)
        self._text.see("end")
        self._text.config(state="disabled")

    def _clear(self):
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.config(state="disabled")

    def stop(self):
        """Stop the consumer thread."""
        self.running = False