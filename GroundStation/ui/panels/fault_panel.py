import tkinter as tk
from tkinter import ttk
from core.constants import TLM

FAULTS = [
    (TLM.FLT_IMU_TILT,    "TILT"),
    (TLM.FLT_MOT_STALL_1, "L MTR\nSTALL"),
    (TLM.FLT_MOT_STALL_2, "R MTR\nSTALL"),
]

class FaultPanel(ttk.LabelFrame):
    def __init__(self, parent, telemetry):
        super().__init__(parent, text="Faults")
        self.telemetry = telemetry
        self._fault_buttons = {}
        self._build()

    def _build(self):
        for i, (mnemonic, label) in enumerate(FAULTS):
            btn = FaultButton(self, label)
            btn.grid(row=0, column=i, padx=3, pady=4)
            self._fault_buttons[mnemonic] = btn

    def refresh(self):
        for mnemonic, btn in self._fault_buttons.items():
            btn.set(self.telemetry.get(mnemonic))


class FaultButton(tk.Label):
    ACTIVE  = {"bg": "#cc2200", "fg": "white"}
    WARNING = {"bg": "#cc8800", "fg": "white"}
    NOMINAL = {"bg": "#444444", "fg": "#aaaaaa"}

    def __init__(self, parent, label, **kwargs):
        super().__init__(parent, text=label, font=("Arial", 9, "bold"),
                         width=8, height=2, relief="flat",
                         **{**self.NOMINAL, **kwargs})
        self.set(None)

    def set(self, state):
        style = {
            True:   self.ACTIVE,
            "warn": self.WARNING,
            False:  self.NOMINAL,
            None:   self.NOMINAL,
        }.get(state, self.NOMINAL)
        self.config(**style)