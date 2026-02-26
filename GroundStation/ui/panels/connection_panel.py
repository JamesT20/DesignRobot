import tkinter as tk
from tkinter import ttk
from core.constants import ConnState

STATE_COLORS = {
    ConnState.DISCONNECTED: "#888888",
    ConnState.CONNECTING:   "#f0a500",
    ConnState.CONNECTED:    "#00cc44",
    ConnState.RECONNECTING: "#f0a500",
    ConnState.ERROR:        "#cc0000",
}

class ConnectionPanel(ttk.LabelFrame):
    def __init__(self, parent, conn):
        super().__init__(parent, text="Connection")
        self.conn = conn
        self.conn.on_state_change = self._on_state_change

        self._host_var = tk.StringVar(value="127.0.0.1")
        self._port_var = tk.StringVar(value="8080")

        ttk.Label(self, text="Host").grid(row=0, column=0, padx=5)
        ttk.Entry(self, textvariable=self._host_var, width=16).grid(row=0, column=1, padx=5)
        ttk.Label(self, text="Port").grid(row=0, column=2, padx=5)
        ttk.Entry(self, textvariable=self._port_var, width=6).grid(row=0, column=3, padx=5)

        self._btn = ttk.Button(self, text="Connect", command=self._toggle)
        self._btn.grid(row=0, column=4, padx=10)

        self._status_dot = tk.Label(self, text="●", fg="#888888", font=("Arial", 16))
        self._status_dot.grid(row=0, column=5, padx=5)

        self._status_lbl = ttk.Label(self, text="Disconnected")
        self._status_lbl.grid(row=0, column=6, padx=5)

    def _toggle(self):
        if self.conn.state == ConnState.CONNECTED:
            self.conn.disconnect()
        else:
            self.conn.connect(self._host_var.get(), int(self._port_var.get()))

    def _on_state_change(self, state: ConnState):
        color = STATE_COLORS.get(state, "#888888")
        self._status_dot.config(fg=color)
        self._status_lbl.config(text=state.value)
        self._btn.config(text="Disconnect" if state == ConnState.CONNECTED else "Connect")