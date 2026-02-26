import tkinter as tk
from tkinter import ttk
from core.constants import TLM

DISPLAY_MAP = [
    (TLM.PWR_BAT_VOLT,   "Battery Voltage",  "V",    6.8,  8.4),
    (TLM.PWR_BAT_CUR,      "Current",          "A",    0,    3.0),
    (TLM.TMP_PROBE,     "Temperature",      "°C",   0,    60),
]

class TelemetryPanel(ttk.LabelFrame):
    def __init__(self, parent, telemetry):
        super().__init__(parent, text="Telemetry")
        self.telemetry = telemetry
        self._vars     = {}

        for i, (mnemonic, label, unit, lo, hi) in enumerate(DISPLAY_MAP):
            var = tk.StringVar(value="--")
            self._vars[mnemonic] = var
            ttk.Label(self, text=label, width=16, anchor="w").grid(row=i, column=0, padx=5, pady=2)
            ttk.Label(self, textvariable=var, width=10, anchor="e").grid(row=i, column=1, padx=2)
            ttk.Label(self, text=unit, width=5, anchor="w").grid(row=i, column=2, padx=2)

    def refresh(self):
        for mnemonic, var in self._vars.items():
            val = self.telemetry.get(mnemonic)
            var.set(f"{val:.2f}" if isinstance(val, float) else str(val) if val is not None else "--")