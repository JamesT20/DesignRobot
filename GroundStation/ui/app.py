import tkinter as tk
from ui.panels.connection_panel import ConnectionPanel
from ui.panels.telemetry_panel import TelemetryPanel
from ui.panels.command_panel import CommandPanel
from ui.panels.camera_panel import CameraPanel
from ui.panels.fault_panel import FaultPanel
from ui.panels.log_panel import LogPanel
from ui.panels.orientation_panel import OrientationPanel
from ui.panels.clock_panel import ClockPanel
from ui.theme import Theme
Theme = Theme()

import queue
from core.logger import get_logger

logger = get_logger("ui.app")
POLL_INTERVAL_MS = 50

class App:
    def __init__(self, root, telemetry, conn, rx_queue, tx_queue, frame_queue, log_queue):
        self.root        = root
        self.telemetry   = telemetry
        self.conn        = conn
        self.rx_queue    = rx_queue
        self.tx_queue    = tx_queue
        self.frame_queue = frame_queue
        self.log_queue   = log_queue
        
 
        # Apply comprehensive palette for all widgets
        root.tk_setPalette(
            background=Theme.BG,
            foreground=Theme.TEXT,
            activeBackground=Theme.PANEL_BG,
            activeforeground=Theme.ACCENT,
            selectBackground=Theme.ERROR_COLOR,
            selectForeground="white"
        )
        root.option_add("*Font", (Theme.FONT_MONO, Theme.FONT_SIZE_M))
        root.option_add("*Button*highlightBackground", Theme.BG)
        root.option_add("*Button*highlightThickness", 0)
        root.option_add("*Scrollbar*background", Theme.PANEL_BG)
        root.option_add("*Scrollbar*troughBackground", Theme.BG)
        root.title("DUI GUI")
        root.geometry("1280x800")
        root.minsize(1024, 600)

        self._build_layout()
        self._poll()
        logger.info("GUI initialized successfully")

    def _build_layout(self):

        self.left_frame = tk.Frame(self.root)
        self.middle_frame = tk.Frame(self.root)
        self.right_frame = tk.Frame(self.root)

        self.left_frame.pack(side="left", fill="both", expand=True)
        self.middle_frame.pack(side="left", fill="both", expand=True)
        self.right_frame.pack(side="left", fill="both", expand=True)

        self.conn_panel  = ConnectionPanel(self.left_frame, self.conn)
        self.cmd_panel   = CommandPanel(self.left_frame, self.tx_queue)
        self.cam_panel   = CameraPanel(self.left_frame, self.frame_queue)

        self.clock_panel = ClockPanel(self.middle_frame)
        self.view_panel  = OrientationPanel(self.middle_frame, self.telemetry)
        self.fault_panel = FaultPanel(self.middle_frame, self.telemetry)
        self.log_panel   = LogPanel(self.middle_frame, self.log_queue)

        self.tlm_panel   = TelemetryPanel(self.right_frame, self.telemetry)

        self.conn_panel.pack(fill="x", padx=Theme.PADDING_M, pady=Theme.PADDING_M)
        self.cam_panel.pack(fill="x", padx=Theme.PADDING_M, pady=Theme.PADDING_M)
        self.cmd_panel.pack(fill="both", expand=True, padx=Theme.PADDING_M, pady=Theme.PADDING_M)
       
        self.clock_panel.pack(fill="x", padx=Theme.PADDING_M, pady=Theme.PADDING_M)
        self.view_panel.pack(fill="both", expand=True, padx=Theme.PADDING_M, pady=Theme.PADDING_M)
        self.fault_panel.pack(fill="x", padx=Theme.PADDING_M, pady=Theme.PADDING_M)
        self.log_panel.pack(fill="both", expand=True, padx=Theme.PADDING_M, pady=Theme.PADDING_M)

        self.tlm_panel.pack(fill="both", expand=True, padx=Theme.PADDING_M, pady=Theme.PADDING_M)

    def _poll(self):
        # Drain telemetry queue
        try:
            for _ in range(20):  # max 20 messages per poll cycle
                msg = self.rx_queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass

        self.root.after(POLL_INTERVAL_MS, self._poll)

    def _handle_message(self, msg: dict):
        try:
            mtype = msg.get("type")
            if mtype == "tlm":
                self.telemetry.update(msg)
                self.tlm_panel.refresh()
                self.fault_panel.refresh()
                self.view_panel.refresh()
            elif mtype == "fault":
                self.fault_panel.add_fault(msg)
            elif mtype == "ack":
                self.log_panel.log(f"ACK {msg.get('cmd')} → {msg.get('status')}")
            elif mtype == "log":
                # DUI sends logs with: timestamp, level, source, message, optional context
                dui_level = msg.get("level", "INFO").upper()
                dui_source = msg.get("source", "DUI")
                dui_msg = msg.get("message", "")
                log_text = f"[{dui_source}] {dui_msg}"
                self.log_panel.log(log_text, dui_level)
                logger.info(f"DUI Log [{dui_source}] {dui_msg}")
            elif mtype == "pong":
                pass  # update heartbeat state
            else:
                logger.warning(f"Unknown message type: {mtype}")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    def on_close(self):
        logger.info("Closing application")
        self.log_panel.stop()
        self.conn.disconnect()
        self.root.destroy()