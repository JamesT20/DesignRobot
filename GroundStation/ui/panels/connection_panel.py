import tkinter as tk
from core.constants import ConnState
from ui.theme import Theme
Theme = Theme()

STATE_COLORS = {
    ConnState.DISCONNECTED: "#888888",
    ConnState.CONNECTING:   "#f0a500",
    ConnState.CONNECTED:    "#00cc44",
    ConnState.RECONNECTING: "#f0a500",
    ConnState.ERROR:        "#cc0000",
}

class ConnectionPanel(tk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent,highlightbackground=Theme.PANEL_EDGE,highlightcolor=Theme.PANEL_EDGE,highlightthickness=3)
        self.conn = conn
        self.conn.on_state_change = self._on_state_change

        self._host_var = tk.StringVar(value="127.0.0.1")
        self._port_var = tk.StringVar(value="8080")

        tk.Label(self, text="Host").grid(row=0, column=0, padx=5)
        tk.Entry(self, textvariable=self._host_var, width=16).grid(row=0, column=1, padx=5)
        tk.Label(self, text="Port").grid(row=0, column=2, padx=5)
        tk.Entry(self, textvariable=self._port_var, width=6).grid(row=0, column=3, padx=5)

        self._btn = tk.Button(self, text="Connect", command=self._toggle)
        self._btn.grid(row=0, column=4, padx=10)

        self._status_dot = tk.Label(self, text="●", fg="#888888", font=("Arial", 16))
        self._status_dot.grid(row=0, column=5, padx=5)

        self._status_lbl = tk.Label(self, text="Disconnected")
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