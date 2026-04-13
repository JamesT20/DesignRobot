import tkinter as tk
from PIL import ImageTk, Image
import io
import queue
from ui.theme import Theme
Theme = Theme()

class CameraPanel(tk.Frame):
    def __init__(self, parent, frame_queue):
        super().__init__(parent,highlightbackground=Theme.PANEL_EDGE,highlightcolor=Theme.PANEL_EDGE,highlightthickness=3)
        self.frame_queue = frame_queue
        self._image_ref  = None  # must hold reference or GC collects it

        self.video_label = tk.Label(self,bg="black")
        self.video_label.pack(padx=5, pady=5)

        self._update()

    def _update(self):
        try:
            jpg  = self.frame_queue.get_nowait()
            img  = Image.open(io.BytesIO(jpg))
            img  = img.resize((320, 240))
            photo = ImageTk.PhotoImage(img)
            self.video_label.configure(image=photo)
            self.video_label.image = photo
        except queue.Empty:
            pass
        self.after(33, self._update)  # ~30fps attempt