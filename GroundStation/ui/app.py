import tkinter as tk
from ui.panels.connection_panel import ConnectionPanel
from ui.panels.telemetry_panel import TelemetryPanel
from ui.panels.command_panel import CommandPanel
from ui.panels.camera_panel import CameraPanel
from ui.panels.fault_panel import FaultPanel
from ui.panels.log_panel import LogPanel
#from core.faults import FaultManager
import queue

POLL_INTERVAL_MS = 50

class App:
    def __init__(self, root, telemetry, conn, camera, rx_queue, tx_queue, frame_queue):
        self.root        = root
        self.telemetry   = telemetry
        self.conn        = conn
        self.camera      = camera
        self.rx_queue    = rx_queue
        self.tx_queue    = tx_queue
        self.frame_queue = frame_queue
       # self.faults      = FaultManager(telemetry, cfg={})

        root.title("DUI GUI")
        root.geometry("1280x800")
        root.minsize(1024, 600)

        self._build_layout()
        self._poll()

    def _build_layout(self):
        self.conn_panel  = ConnectionPanel(self.root, self.conn)
        self.tlm_panel   = TelemetryPanel(self.root, self.telemetry)
        self.cmd_panel   = CommandPanel(self.root, self.tx_queue)
        self.cam_panel   = CameraPanel(self.root, self.frame_queue)
        self.fault_panel = FaultPanel(self.root)
        self.log_panel   = LogPanel(self.root)

        self.conn_panel.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.tlm_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.cmd_panel.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.cam_panel.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.fault_panel.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
        self.log_panel.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

    def _poll(self):
        # Drain telemetry queue
        try:
            for _ in range(20):  # max 20 messages per poll cycle
                msg = self.rx_queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass

        # Check faults
        # new_faults = self.faults.check()
        # for f in new_faults:
        #     self.fault_panel.add_fault(f)
        #     self.log_panel.log(f["msg"], level=f["severity"].value)

        self.root.after(POLL_INTERVAL_MS, self._poll)

    def _handle_message(self, msg: dict):
        mtype = msg.get("type")
        if mtype == "tlm":
            self.telemetry.update(msg)
            self.tlm_panel.refresh()
        elif mtype == "fault":
            self.fault_panel.add_fault(msg)
        elif mtype == "ack":
            self.log_panel.log(f"ACK {msg.get('cmd')} → {msg.get('status')}")
        elif mtype == "pong":
            pass  # update heartbeat state

    def on_close(self):
        self.conn.disconnect()
        # self.camera.stop()
        self.root.destroy()