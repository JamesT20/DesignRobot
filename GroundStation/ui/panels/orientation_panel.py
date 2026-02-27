import tkinter as tk
from tkinter import ttk
import numpy as np
import struct
import math
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.constants import TLM

BG     = "#050a07"
BORDER = "#1a3a20"
ACCENT = "#00ff66"
CYAN   = "#00ddff"
DIM    = "#0d2a12"


# ── geometry ──────────────────────────────────────────────────────────────────

def make_default_faces():
    l, w, h = 1.2, 0.8, 0.35
    x, y, z = l/2, w/2, h/2
    def box(verts):
        return [
            [verts[0],verts[1],verts[2],verts[3]],
            [verts[4],verts[5],verts[6],verts[7]],
            [verts[0],verts[1],verts[5],verts[4]],
            [verts[2],verts[3],verts[7],verts[6]],
            [verts[1],verts[2],verts[6],verts[5]],
            [verts[0],verts[3],verts[7],verts[4]],
        ]
    body = np.array([[-x,-y,-z],[x,-y,-z],[x,y,-z],[-x,y,-z],
                     [-x,-y,z],[x,-y,z],[x,y,z],[-x,y,z]])
    bx, by, bz, ox, oz = 0.2, 0.2, 0.15, 0.2, z
    bump = np.array([[ox-bx,-by,oz],[ox+bx,-by,oz],[ox+bx,by,oz],[ox-bx,by,oz],
                     [ox-bx,-by,oz+2*bz],[ox+bx,-by,oz+2*bz],[ox+bx,by,oz+2*bz],[ox-bx,by,oz+2*bz]])
    return box(body) + box(bump)


def load_stl(filepath):
    faces = []
    with open(filepath, "rb") as f:
        f.read(80)
        try:
            num_triangles = struct.unpack("<I", f.read(4))[0]
            import os
            is_binary = (80 + 4 + num_triangles * 50 == os.path.getsize(filepath))
        except Exception:
            is_binary = False

    if is_binary:
        with open(filepath, "rb") as f:
            f.read(84)
            for _ in range(num_triangles):
                f.read(12)
                verts = [np.array(struct.unpack("<3f", f.read(12)), dtype=float) for _ in range(3)]
                f.read(2)
                faces.append(verts)
    else:
        with open(filepath, "r", errors="replace") as f:
            text = f.read()
        import re
        pat = re.compile(
            r"facet\s+normal[^\n]*\n\s*outer loop\s*\n"
            r"\s*vertex\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s*\n"
            r"\s*vertex\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s*\n"
            r"\s*vertex\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)\s*\n"
            r"\s*endloop", re.IGNORECASE)
        for m in pat.finditer(text):
            vals = list(map(float, m.groups()))
            faces.append([np.array(vals[i:i+3]) for i in range(0, 9, 3)])

    if not faces:
        raise ValueError("No triangles found in STL file.")

    all_verts = np.array([v for face in faces for v in face])
    center = (all_verts.max(axis=0) + all_verts.min(axis=0)) / 2
    scale  = np.linalg.norm(all_verts.max(axis=0) - all_verts.min(axis=0)) / 2
    if scale == 0: scale = 1.0
    return [[(v - center) / scale for v in face] for face in faces]


def rotation_matrix(roll_deg, pitch_deg, yaw_deg):
    r, p, y = np.radians(roll_deg), np.radians(pitch_deg), np.radians(yaw_deg)
    Rx = np.array([[1,0,0],[0,np.cos(r),-np.sin(r)],[0,np.sin(r),np.cos(r)]])
    Ry = np.array([[np.cos(p),0,np.sin(p)],[0,1,0],[-np.sin(p),0,np.cos(p)]])
    Rz = np.array([[np.cos(y),-np.sin(y),0],[np.sin(y),np.cos(y),0],[0,0,1]])
    return Rz @ Ry @ Rx


# ── widget ────────────────────────────────────────────────────────────────────

class OrientationPanel(ttk.LabelFrame):

    def __init__(self, parent, telemetry, size=3.5, **kwargs):
        super().__init__(parent, text="Orientation", **kwargs)
        self.telemetry = telemetry
        self._size = size
        self._roll = self._pitch = self._yaw = 0.0
        self._base_faces = make_default_faces()
        self._stl_loaded = False
        self._build()

    # ── public ────────────────────────────────────────────────────────────────

    def refresh(self):
        roll  = self.telemetry.get(TLM.IMU_ROLL)
        pitch = self.telemetry.get(TLM.IMU_PITCH)
        yaw   = self.telemetry.get(TLM.IMU_HEADING)

        roll  = float(roll)  if roll  is not None else 0.0
        pitch = float(pitch) if pitch is not None else 0.0
        yaw   = float(yaw)   if yaw   is not None else 0.0

        if (roll, pitch, yaw) != (self._roll, self._pitch, self._yaw):
            self._roll, self._pitch, self._yaw = roll, pitch, yaw
            self._draw()

    def load_stl(self, filepath):
        """Replace default box mesh with an STL file."""
        self._base_faces = load_stl(filepath)
        self._stl_loaded = True
        self._draw()

    # ── internal ──────────────────────────────────────────────────────────────

    def _build(self):
        self._fig = plt.Figure(figsize=(self._size, self._size), facecolor=BG)
        self._ax  = self._fig.add_subplot(111, projection="3d", computed_zorder=False)
        self._ax.set_facecolor(BG)
        self._fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self._ax.set_axis_off()
        self._ax.set_xlim(-1.2, 1.2)
        self._ax.set_ylim(-1.2, 1.2)
        self._ax.set_zlim(-1.2, 1.2)
        self._ax.set_box_aspect([1, 1, 1])

        for label, pos, col in [("X+", (1.3,0,0), "#ff4444"),
                                  ("Y+", (0,1.3,0), ACCENT),
                                  ("Z+", (0,0,1.3), CYAN)]:
            self._ax.text(*pos, label, color=col, fontsize=7,
                          fontfamily="Courier New", ha="center", va="center")

        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().configure(highlightthickness=0)
        self._canvas.get_tk_widget().pack(padx=4, pady=4)

        self._draw()

    def _draw(self):
        for attr in ("_mesh", "_floor"):
            if hasattr(self, attr):
                try: getattr(self, attr).remove()
                except: pass

        R = rotation_matrix(self._roll, self._pitch, self._yaw)
        rotated = [[R @ np.array(v) for v in face] for face in self._base_faces]

        # Floor first (behind)
        s = 1.1
        xs = np.linspace(-s, s, 9)
        ys = np.linspace(-s, s, 9)
        floor_verts = [
            [[xs[i], ys[j], -1.05], [xs[i+1], ys[j], -1.05],
             [xs[i+1], ys[j+1], -1.05], [xs[i], ys[j+1], -1.05]]
            for i in range(len(xs)-1) for j in range(len(ys)-1)
        ]
        self._floor = Poly3DCollection(floor_verts, edgecolor=DIM,
                                        facecolor=(0.01, 0.06, 0.02, 0.4),
                                        linewidth=0.3, zorder=1)
        self._ax.add_collection3d(self._floor)

        # Mesh on top
        ec = CYAN if self._stl_loaded else ACCENT
        lw = 0.35 if self._stl_loaded else 0.6
        self._mesh = Poly3DCollection(rotated, edgecolor=ec,
                                       facecolor=(0.02, 0.08, 0.04, 0.55),
                                       linewidth=lw, zorder=2)
        self._ax.add_collection3d(self._mesh)
        self._canvas.draw_idle()