import tkinter as tk
from core.constants import TLM
from ui.theme import Theme
Theme = Theme()

FAULTS = [
    (TLM.FLT_IMU_TILT,    "TILT"),
    (TLM.FLT_MOT_STALL_1, "L MTR\nSTALL"),
    (TLM.FLT_MOT_STALL_2, "R MTR\nSTALL"),
]

class FaultPanel(tk.Frame):
    def __init__(self, parent, telemetry):
        super().__init__(parent,highlightbackground=Theme.PANEL_EDGE,highlightcolor=Theme.PANEL_EDGE,highlightthickness=3)
        self.telemetry = telemetry
        self._fault_buttons = {}
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)  # left spacer
        for i, (mnemonic, label) in enumerate(FAULTS):
            btn = FaultButton(self, label)
            btn.grid(row=0, column=i+1, padx=3, pady=4)
            self._fault_buttons[mnemonic] = btn
        self.columnconfigure(len(FAULTS)+1, weight=1)  # right spacer

    def refresh(self):
        for mnemonic, btn in self._fault_buttons.items():
            btn.set(self.telemetry.get(mnemonic))


class FaultButton(tk.Label):
    ACTIVE  = {"bg": "#cc2200", "fg": "white"}
    WARNING = {"bg": "#cc8800", "fg": "white"}
    NOMINAL = {"bg": "#444444", "fg": "#aaaaaa"}

    def __init__(self, parent, label, **kwargs):
        super().__init__(parent, text=label,
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