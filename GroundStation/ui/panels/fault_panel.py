import tkinter as tk
from tkinter import ttk
import time

SEVERITY_COLORS = {
    "INFO":     "#ffffff",
    "WARN":     "#f0a500",
    "FAULT":    "#ff6600",
    "CRITICAL": "#cc0000",
}

class FaultPanel(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Faults")
        self._tree = ttk.Treeview(self, columns=("time", "severity", "fault", "msg"), show="headings", height=8)
        self._tree.heading("time",     text="Time")
        self._tree.heading("severity", text="Severity")
        self._tree.heading("fault",    text="Mnemonic")
        self._tree.heading("msg",      text="Message")
        self._tree.column("time",      width=80)
        self._tree.column("severity",  width=70)
        self._tree.column("fault",     width=160)
        self._tree.column("msg",       width=250)
        self._tree.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Button(self, text="Clear", command=self._clear).pack(pady=2)

    def add_fault(self, fault: dict):
        ts  = time.strftime("%H:%M:%S")
        sev = fault.get("severity", "INFO")
        if hasattr(sev, "value"):
            sev = sev.value
        self._tree.insert("", 0, values=(ts, sev, fault.get("flt", ""), fault.get("msg", "")))

    def _clear(self):
        for row in self._tree.get_children():
            self._tree.delete(row)