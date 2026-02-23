import tkinter as tk

class StatusLED(tk.Label):
    def set_connected(self, connected: bool):
        self.config(text="●", fg="green" if connected else "red")

class ConsoleLog(tk.Text):
    def log(self, message: str):
        self.insert(tk.END, message + "\n")
        self.see(tk.END)

class Gauge(tk.Label):
    def update_value(self, label: str, value: float, unit: str = ""):
        self.config(text=f"{label}: {value:.2f} {unit}")