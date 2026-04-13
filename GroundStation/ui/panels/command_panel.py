import tkinter as tk
from tkinter import messagebox
from core import commands
from ui.theme import Theme

Theme = Theme()

_DIR_MAP = {
    "forward": ( 1,  1),
    "reverse": (-1, -1),
    "left":    (-1,  1),
    "right":   ( 1, -1),
    "stop":    ( 0,  0),
}


class CommandPanel(tk.Frame):
    def __init__(self, parent, tx_queue):
        super().__init__(
            parent,
            highlightbackground=Theme.PANEL_EDGE,
            highlightcolor=Theme.PANEL_EDGE,
            highlightthickness=3,
        )
        self.tx_queue = tx_queue
        self._queue: list[dict] = []   # local step list

        self._build_ui()

    # ── UI layout ────────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 4, "pady": 3}

        # ── Direction buttons ──────────────────────────────────────────────
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=0, column=0, columnspan=2, pady=(8, 4))

        tk.Button(btn_frame, text="▲ Forward",
                  command=lambda: self._add_dir("forward")).grid(
                  row=0, column=1, **pad)
        tk.Button(btn_frame, text="◀ Left",
                  command=lambda: self._add_dir("left")).grid(
                  row=1, column=0, **pad)
        tk.Button(btn_frame, text="■ Stop",
                  command=lambda: self._add_dir("stop")).grid(
                  row=1, column=1, **pad)
        tk.Button(btn_frame, text="▶ Right",
                  command=lambda: self._add_dir("right")).grid(
                  row=1, column=2, **pad)
        tk.Button(btn_frame, text="▼ Reverse",
                  command=lambda: self._add_dir("reverse")).grid(
                  row=2, column=1, **pad)

        # ── Wait input ────────────────────────────────────────────────────
        wait_frame = tk.Frame(self)
        wait_frame.grid(row=1, column=0, columnspan=2, pady=4)

        tk.Label(wait_frame, text="Wait (ms):").pack(side="left", padx=4)
        self._wait_var = tk.IntVar(value=500)
        tk.Spinbox(wait_frame, from_=0, to=30000, increment=100,
                   textvariable=self._wait_var, width=6).pack(side="left")
        tk.Button(wait_frame, text="⏱ Add Wait",
                  command=self._add_wait).pack(side="left", padx=6)

        # ── Queue listbox ─────────────────────────────────────────────────
        tk.Label(self, text="Command queue:").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 0))

        list_frame = tk.Frame(self)
        list_frame.grid(row=3, column=0, columnspan=2, padx=8, pady=2, sticky="ew")

        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        self._listbox = tk.Listbox(
            list_frame, height=8, width=30,
            yscrollcommand=scrollbar.set, selectmode="single",
        )
        scrollbar.config(command=self._listbox.yview)
        self._listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Queue controls ────────────────────────────────────────────────
        ctrl_frame = tk.Frame(self)
        ctrl_frame.grid(row=4, column=0, columnspan=2, pady=4)

        tk.Button(ctrl_frame, text="Remove selected",
                  command=self._remove_selected).pack(side="left", padx=4)
        tk.Button(ctrl_frame, text="Clear all",
                  command=self._clear_queue).pack(side="left", padx=4)

        # ── Send / ESTOP ──────────────────────────────────────────────────
        tk.Button(self, text="Send sequence →",
                  command=self._send_sequence).grid(
                  row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=4)

        estop_btn = tk.Button(
            self, text="E-STOP",
            bg=Theme.ERROR_COLOR, fg="white", font=(Theme.FONT_MONO, Theme.FONT_SIZE_L, "bold"),
            command=self._estop,
        )
        estop_btn.grid(row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=6)

        tk.Button(self, text="Reboot",
                  command=self._reboot).grid(
                  row=7, column=0, columnspan=2, pady=2)

    # ── Queue management ─────────────────────────────────────────────────────

    def _add_dir(self, direction: str):
        l, r = _DIR_MAP[direction]
        label = f"{direction.capitalize()}  (L={l:+d} R={r:+d})"
        self._queue.append(commands._cmd("CMD_MOT_SET_DIR",
                                         left_dir=l, right_dir=r))
        self._listbox.insert("end", label)

    def _add_wait(self):
        ms = max(0, self._wait_var.get())
        self._queue.append(commands._cmd("CMD_SYS_WAIT", ms=ms))
        self._listbox.insert("end", f"Wait  {ms} ms")

    def _remove_selected(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self._listbox.delete(idx)
        del self._queue[idx]

    def _clear_queue(self):
        self._queue.clear()
        self._listbox.delete(0, "end")

    # ── TX actions ───────────────────────────────────────────────────────────

    def _send_sequence(self):
        if not self._queue:
            messagebox.showinfo("Empty queue", "Add at least one command first.")
            return
        msg = commands.sequence(*[
            {"endpoint": "/cmd", "seq": 0, "commands": [c]}
            for c in self._queue
        ])
        self.tx_queue.put(msg)
        self._clear_queue()

    def _estop(self):
        self.tx_queue.put(commands.estop())

    def _reboot(self):
        if messagebox.askyesno("Reboot", "Stop motors and reboot device?"):
            self.tx_queue.put(commands.estop())
            self.tx_queue.put(commands.reboot())