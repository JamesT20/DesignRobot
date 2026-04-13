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
        super().__init__(
            parent,
            highlightbackground=Theme.PANEL_EDGE,
            highlightcolor=Theme.PANEL_EDGE,
            highlightthickness=3,
        )
        self.conn = conn
        self.conn.on_state_change = self._on_state_change

        # ── Row 0: Connection controls ────────────────────────────────────────
        ctrl_frame = tk.Frame(self)
        ctrl_frame.grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))


        self._btn = tk.Button(ctrl_frame, text="Connect", command=self._toggle)
        self._btn.pack(side=tk.LEFT, padx=(0, 10))

        # Connection status
        self._conn_dot = tk.Label(ctrl_frame, text="●", fg="#888888", font=(Theme.FONT_MONO, Theme.FONT_SIZE_M))
        self._conn_dot.pack(side=tk.LEFT, padx=(0, 3))
        self._conn_lbl = tk.Label(ctrl_frame, text="Disconnected",font=(Theme.FONT_MONO, Theme.FONT_SIZE_M))
        self._conn_lbl.pack(side=tk.LEFT, padx=(0, 16))

        # ── Row 1: Info placeholder sections ─────────────────────────────────
        info_frame = tk.Frame(self)
        info_frame.grid(row=1, column=0, sticky="ew", padx=6, pady=(2, 6))
        self.columnconfigure(0, weight=1)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _info_section(self, parent, label: str, default: str, col: int) -> tk.Label:
        """Create a small labelled info cell and return the value Label."""
        cell = tk.Frame(parent, padx=8)
        cell.grid(row=0, column=col, sticky="w")
        tk.Label(cell, text=label, font=(Theme.FONT_MONO, Theme.FONT_SIZE_M), fg="#888888").pack(anchor="w")
        val = tk.Label(cell, text=default, font=(Theme.FONT_MONO, Theme.FONT_SIZE_M,"bold"))
        val.pack(anchor="w")
        return val

    # ── Public helpers (call these from your camera/telemetry callbacks) ──────

    def update_latency(self, ms: float | None):
        self._latency_lbl.config(text=f"{ms:.0f} ms" if ms is not None else "— ms")

    def update_uptime(self, seconds: int | None):
        if seconds is None:
            self._uptime_lbl.config(text="—")
        else:
            h, rem = divmod(seconds, 3600)
            m, s = divmod(rem, 60)
            self._uptime_lbl.config(text=f"{h:02d}:{m:02d}:{s:02d}")

    def update_resolution(self, w: int | None, h: int | None):
        self._resolution_lbl.config(text=f"{w}×{h}" if w and h else "—")

    def update_signal(self, rssi: int | None):
        self._signal_lbl.config(text=f"{rssi} dBm" if rssi is not None else "—")

    # ── Event handlers ────────────────────────────────────────────────────────

    def _toggle(self):
        if self.conn.state == ConnState.CONNECTED:
            self.conn.disconnect()
        else:
            host = "192.168.4.1" 
            self.conn.connect(host)

    def _on_state_change(self, state: ConnState):
        color = STATE_COLORS.get(state, "#888888")
        self._conn_dot.config(fg=color)
        self._conn_lbl.config(text=state.value)
        self._btn.config(text="Disconnect" if state == ConnState.CONNECTED else "Connect")