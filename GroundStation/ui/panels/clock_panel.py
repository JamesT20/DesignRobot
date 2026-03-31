import tkinter as tk
import time
from ui.theme import Theme
Theme = Theme()

class ClockPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent,highlightbackground=Theme.PANEL_EDGE,highlightcolor=Theme.PANEL_EDGE,highlightthickness=3)
        self._time = tk.Label(self,font=(None,Theme.FONT_SIZE_L,"bold"))
        self._time.pack()
        self._tick()
 
    def _tick(self):
        now = time.localtime()
        self._time.config(text=time.strftime("%m/%d/%Y %H:%M:%S", now))
        self.after(1000, self._tick)