import tkinter as tk

class TelemetryPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.temp_label = tk.Label(self, text="Temp: --")
        self.volt_label = tk.Label(self, text="Voltage: --")
        self.temp_label.pack()
        self.volt_label.pack()

    def update(self, telemetry):
        color = "red" if telemetry.temperature > 80 else "black"
        self.temp_label.config(text=f"Temp: {telemetry.temperature:.1f} °C", fg=color)
        self.volt_label.config(text=f"Voltage: {telemetry.voltage:.2f} V")