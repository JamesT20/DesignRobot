import queue
import tkinter as tk
from network.connection_manager import ConnectionManager
# from network.camera_thread import CameraThread
from core.telemetry import TelemetryStore
from ui.app import App

def main():
    # Shared queues — the only thing that crosses layer boundaries
    rx_queue    = queue.Queue(maxsize=1000)
    tx_queue    = queue.Queue(maxsize=100)
    frame_queue = queue.Queue(maxsize=5)

    telemetry   = TelemetryStore()
    conn        = ConnectionManager(rx_queue, tx_queue)
    camera      = None # CameraThread(frame_queue)

    root = tk.Tk()
    app  = App(root, telemetry, conn, camera, rx_queue, tx_queue, frame_queue)

    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()