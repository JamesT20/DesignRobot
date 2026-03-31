import tkinter as tk
from PIL import ImageTk
import queue
from ui.theme import Theme
Theme = Theme()

class CameraPanel(tk.Frame):
    def __init__(self, parent, frame_queue):
        super().__init__(parent,highlightbackground=Theme.PANEL_EDGE,highlightcolor=Theme.PANEL_EDGE,highlightthickness=3)
        self.frame_queue = frame_queue
        self._image_ref  = None  # must hold reference or GC collects it

        self._canvas = tk.Canvas(self,bg="black")
        self._canvas.pack(padx=5, pady=5)

        self._fps_var = tk.StringVar(value="FPS: --")
        tk.Label(self, textvariable=self._fps_var).pack()

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