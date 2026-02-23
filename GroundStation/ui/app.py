import tkinter as tk
from ui.widgets import StatusLED, ConsoleLog
from ui.telemetry_panel import TelemetryPanel

# define the app
class App(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title("Ground Control")
        self.geometry("800x600")

        # build widgets
        self.led = StatusLED(self)
        self.led.pack()
        self.telemetry_panel = TelemetryPanel(self)
        self.telemetry_panel.pack()
        self.console = ConsoleLog(self, height=8)
        self.console.pack(fill=tk.X)

        # callback func to update all data
        controller.ui_callback = self._on_message

        # refresh once on startup
        self._refresh()

    # update specific telemetry panel
    def _on_message(self, msg):
        self.telemetry_panel.update(msg)
        self.console.log(str(msg))

    # loops to set connected state
    def _refresh(self):
        connected = self.controller.state.connected
        self.led.set_connected(connected)
        self.after(500, self._refresh)