import tkinter as tk
from tkinter import ttk
import time

LEVEL_COLORS = {"INFO": "white", "WARN": "#f0a500", "FAULT": "#ff6600", "CRITICAL": "#cc0000"}

class LogPanel(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Log")
        self._text = tk.Text(self, height=6, state="disabled", bg="#1e1e1e", fg="white",
                             font=("Courier", 9), wrap="word")
        scroll = ttk.Scrollbar(self, command=self._text.yview)
        self._text.config(yscrollcommand=scroll.set)
        self._text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for level, color in LEVEL_COLORS.items():
            self._text.tag_config(level, foreground=color)

        ttk.Button(self, text="Clear", command=self._clear).pack(pady=2)

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