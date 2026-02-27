import tkinter as tk
from tkinter import ttk
from core.constants import TLM

SECTIONS = [
    ("Battery",  [(TLM.PWR_BAT_VOLT, "Voltage", "V"), (TLM.PWR_BAT_CUR, "Current", "A")]),
    ("IMU",      [(TLM.IMU_HEADING, "Heading", "°"), (TLM.IMU_ROLL, "Roll", "°"), (TLM.IMU_PITCH, "Pitch", "°")]),
    ("Payload",  [(TLM.TMP_PROBE, "Temp", "°C")]),
    ("System",   [(TLM.SYS_MODE, "Status", ""), (TLM.SYS_UPTIME, "Uptime", "s"),
                  (TLM.SYS_HEAP_FREE, "Heap", "mb"), (TLM.SYS_PACKET_NUM, "Packet", "")]),
    ("L Motor",  [(TLM.MOT_1_SPEED, "Speed", "%"), (TLM.MOT_1_DIR, "Direction", ""),
                  (TLM.PWR_MOT1_VOLT, "Voltage", "V"), (TLM.PWR_MOT1_CUR, "Current", "A")]),
    ("R Motor",  [(TLM.MOT_2_SPEED, "Speed", "%"), (TLM.MOT_2_DIR, "Direction", ""),
                  (TLM.PWR_MOT2_VOLT, "Voltage", "V"), (TLM.PWR_MOT2_CUR, "Current", "A")]),
]

class TelemetryPanel(ttk.LabelFrame):
    def __init__(self, parent, telemetry):
        super().__init__(parent, text="Telemetry")
        self.telemetry = telemetry
        self._vars = {}
        self._build()

    def _build(self):
        for col_offset, (section_name, fields) in enumerate(SECTIONS):
            base_col = col_offset * 4  # 4 grid columns per section: spacer, label, value, unit

            ttk.Label(self, text=section_name, font=("", 9, "bold")).grid(
                row=0, column=base_col, columnspan=3, sticky="w", padx=(10, 2), pady=(4, 0)
            )
            for row, (mnemonic, label, unit) in enumerate(fields, start=1):
                var = tk.StringVar(value="--")
                self._vars[mnemonic] = var
                ttk.Label(self, text=label, width=10, anchor="w").grid(row=row, column=base_col,     padx=(10, 2), pady=1)
                ttk.Label(self, textvariable=var,  width=8,  anchor="e").grid(row=row, column=base_col + 1, padx=2)
                ttk.Label(self, text=unit,         width=4,  anchor="w").grid(row=row, column=base_col + 2, padx=2)

    def refresh(self):
        for mnemonic, var in self._vars.items():
            val = self.telemetry.get(mnemonic)
            var.set(f"{val:.2f}" if isinstance(val, float) else str(val) if val is not None else "--")