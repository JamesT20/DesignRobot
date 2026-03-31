import tkinter as tk
import time
from ui.theme import Theme
Theme = Theme()

LEVEL_COLORS = {"INFO": "white", "WARN": "#f0a500", "FAULT": "#ff6600", "CRITICAL": "#cc0000"}

class LogPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent,highlightbackground=Theme.PANEL_EDGE,highlightcolor=Theme.PANEL_EDGE,highlightthickness=3)
        self._text = tk.Text(self, height=6, state="disabled", wrap="word")
        scroll = tk.Scrollbar(self, command=self._text.yview)
        self._text.config(yscrollcommand=scroll.set)
        self._text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for level, color in LEVEL_COLORS.items():
            self._text.tag_config(level, foreground=color)

        tk.Button(self, text="Clear", command=self._clear).pack(pady=2)

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