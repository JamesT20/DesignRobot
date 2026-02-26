import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
import queue

class CameraPanel(ttk.LabelFrame):
    def __init__(self, parent, frame_queue):
        super().__init__(parent, text="Camera")
        self.frame_queue = frame_queue
        self._image_ref  = None  # must hold reference or GC collects it

        self._canvas = tk.Canvas(self, width=320, height=240, bg="black")
        self._canvas.pack(padx=5, pady=5)

        self._fps_var = tk.StringVar(value="FPS: --")
        ttk.Label(self, textvariable=self._fps_var).pack()

        self._update()

    def _update(self):
        try:
            img  = self.frame_queue.get_nowait()
            img  = img.resize((320, 240))
            photo = ImageTk.PhotoImage(img)
            self._canvas.create_image(0, 0, anchor="nw", image=photo)
            self._image_ref = photo  # prevent garbage collection
        except queue.Empty:
            pass
        self.after(33, self._update)  # ~30fps attempt