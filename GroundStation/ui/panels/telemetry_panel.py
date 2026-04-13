import tkinter as tk
from core.constants import TLM
from ui.theme import Theme
Theme = Theme()

SECTIONS = [
    ("Battery",  [(TLM.PWR_BAT_VOLT, "Voltage", "V"), (TLM.PWR_BAT_CUR, "Current", "A")]),
    ("IMU",      [(TLM.IMU_HEADING, "Heading", "°"), (TLM.IMU_ROLL, "Roll", "°"), (TLM.IMU_PITCH, "Pitch", "°")]),
    ("Payload",  [(TLM.TMP_PROBE, "Temp", "°C")]),
    ("System",   [(TLM.SYS_MODE, "Status", ""), (TLM.SYS_UPTIME, "Uptime", "s"),
                  (TLM.SYS_HEAP_FREE, "Heap", "mb"), (TLM.SYS_PACKET_NUM, "Packet", ""), (TLM.SYS_LOOP_TIME, "Loop Time", "s")]),
    ("L Motor",  [(TLM.MOT_1_SPEED, "Speed", "%"), (TLM.MOT_1_DIR, "Direction", ""),
                  (TLM.PWR_MOT1_VOLT, "Voltage", "V"), (TLM.PWR_MOT1_CUR, "Current", "A")]),
    ("R Motor",  [(TLM.MOT_2_SPEED, "Speed", "%"), (TLM.MOT_2_DIR, "Direction", ""),
                  (TLM.PWR_MOT2_VOLT, "Voltage", "V"), (TLM.PWR_MOT2_CUR, "Current", "A")]),
]

class TelemetryPanel(tk.Frame):
    def __init__(self, parent, telemetry):
        super().__init__(parent,highlightbackground=Theme.PANEL_EDGE,highlightcolor=Theme.PANEL_EDGE,highlightthickness=3)
        self.telemetry = telemetry
        self._vars = {}
        self._build()

    def _build(self):
        row = 0
        for section_name, fields in SECTIONS:
            tk.Label(self, text=section_name, font=(Theme.FONT_MONO, Theme.FONT_SIZE_L, "bold", "underline"), anchor="w").grid(
                row=row, column=0, columnspan=3, sticky="w", padx=(10, 2), pady=(6, 0)
            )
            row += 1
            for mnemonic, label, unit in fields:
                var = tk.StringVar(value="--")
                self._vars[mnemonic] = var
                tk.Label(self, text=label, width=10, anchor="w").grid(row=row, column=0, padx=(10, 2), pady=1)
                tk.Label(self, textvariable=var,  width=8,  anchor="e").grid(row=row, column=1, padx=2)
                tk.Label(self, text=unit,         width=4,  anchor="w").grid(row=row, column=2, padx=2)
                row += 1

    def refresh(self):
        for mnemonic, var in self._vars.items():
            val = self.telemetry.get(mnemonic)
            var.set(f"{val:.2f}" if isinstance(val, float) else str(val) if val is not None else "--")