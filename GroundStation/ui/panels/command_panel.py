import tkinter as tk
from tkinter import ttk
from core import commands

class CommandPanel(ttk.LabelFrame):
    def __init__(self, parent, tx_queue):
        super().__init__(parent, text="Commands")
        self.tx_queue = tx_queue

        # Motor speed sliders
        self._left_var  = tk.IntVar(value=0)
        self._right_var = tk.IntVar(value=0)

        ttk.Label(self, text="Left Motor").grid(row=0, column=0, padx=5, pady=5)
        ttk.Scale(self, from_=-100, to=100, variable=self._left_var, orient="vertical").grid(row=1, column=0, padx=10)

        ttk.Label(self, text="Right Motor").grid(row=0, column=1, padx=5, pady=5)
        ttk.Scale(self, from_=-100, to=100, variable=self._right_var, orient="vertical").grid(row=1, column=1, padx=10)

        ttk.Button(self, text="Send Speed", command=self._send_speed).grid(row=2, column=0, columnspan=2, pady=5)

        # ESTOP — prominent red button
        estop_btn = tk.Button(self, text="E-STOP", bg="red", fg="white",
                              font=("Arial", 14, "bold"), command=self._estop)
        estop_btn.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=10)

        ttk.Button(self, text="Reboot", command=self._reboot).grid(row=4, column=0, columnspan=2, pady=2)

    def _send_speed(self):
        cmd = commands.set_motor_speed(self._left_var.get(), self._right_var.get())
        self.tx_queue.put(cmd)

    def _estop(self):
        self.tx_queue.put(commands.estop())

    def _reboot(self):
        if tk.messagebox.askyesno("Reboot", "Stop motors and reboot device?"):
            self.tx_queue.put(commands.estop())
            self.tx_queue.put(commands.reboot())