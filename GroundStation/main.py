import queue
import tkinter as tk
from network.connection_manager import ConnectionManager
from core.telemetry import TelemetryStore
from core.logger import init_logging
from ui.app import App

def main():
    # Shared queues — the only thing that crosses layer boundaries
    rx_queue    = queue.Queue(maxsize=1000)
    tx_queue    = queue.Queue(maxsize=100)
    frame_queue = queue.Queue(maxsize=5)
    log_queue   = queue.Queue(maxsize=500)  # Queue for logging messages

    # Initialize logging system (UI-only, no file persistence)
    init_logging(log_queue)

    telemetry   = TelemetryStore()
    conn        = ConnectionManager(rx_queue, tx_queue, frame_queue)

    root = tk.Tk()
    app  = App(root, telemetry, conn, rx_queue, tx_queue, frame_queue, log_queue)

    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()