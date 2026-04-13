import tkinter as tk
from core.constants import TLM
from ui.theme import Theme
Theme = Theme()

SECTIONS = [
    ("IMU", [
        (TLM.IMU_HEADING, "Heading", "°"),
        (TLM.IMU_ROLL,    "Roll",    "°"),
        (TLM.IMU_PITCH,   "Pitch",   "°"),
        (TLM.IMU_ACCEL_X, "Accel X", "m/s²"),
        (TLM.IMU_ACCEL_Y, "Accel Y", "m/s²"),
        (TLM.IMU_ACCEL_Z, "Accel Z", "m/s²"),
        (TLM.IMU_GYRO_X,  "Gyro X",  "°/s"),
        (TLM.IMU_GYRO_Y,  "Gyro Y",  "°/s"),
        (TLM.IMU_GYRO_Z,  "Gyro Z",  "°/s"),
    ]),
    ("Payload", [
        (TLM.TMP_PROBE, "Temp", "°C"),
    ]),
    ("System", [
        (TLM.SYS_MODE,        "Mode",      ""),
        (TLM.SYS_STATUS,      "Status",    ""),
        (TLM.SYS_UPTIME,      "Uptime",    "s"),
        (TLM.SYS_HEAP_FREE,   "Heap Free", "B"),
        (TLM.SYS_PACKET_NUM,  "Packet #",  ""),
        (TLM.SYS_LOOP_TIME,   "Loop Time", "ms"),
        (TLM.SYS_TEMP_C,      "CPU Temp",  "°C"),
        (TLM.SYS_CAM_OK,      "Camera",    ""),
        (TLM.SYS_WIFI_RSSI,   "RSSI",      "dBm"),
    ]),
    ("Sequence", [
        (TLM.SEQ_RUNNING,         "Running",   ""),
        (TLM.SEQ_CURRENT,         "Current",   ""),
        (TLM.SEQ_TOTAL,           "Total",     ""),
        (TLM.SEQ_QUEUE_DEPTH,     "Queued",    ""),
        (TLM.SEQ_QUEUE_REMAINING, "Remaining", ""),
    ]),
    ("L Motor", [
        (TLM.MOT_1_DIR_CMD, "Dir Cmd",  ""),
        (TLM.MOT_1_DIR,     "Dir Act",  ""),
        (TLM.PWR_MOT1_VOLT, "Voltage",  "V"),
        (TLM.PWR_MOT1_CUR,  "Current",  "mA"),
    ]),
    ("R Motor", [
        (TLM.MOT_2_DIR_CMD, "Dir Cmd",  ""),
        (TLM.MOT_2_DIR,     "Dir Act",  ""),
        (TLM.PWR_MOT2_VOLT, "Voltage",  "V"),
        (TLM.PWR_MOT2_CUR,  "Current",  "mA"),
    ]),
    ("Faults", [
        (TLM.FLT_IMU_TILT,      "IMU Tilt",  ""),
        (TLM.FLT_MOT_STALL_1,   "Stall L",   ""),
        (TLM.FLT_MOT_STALL_2,   "Stall R",   ""),
        (TLM.FLT_QUEUE_OVERFLOW, "Queue OVF", ""),
        (TLM.MOT_BUSY,           "Mot Busy",  ""),
    ]),
]

# How many sections go in the left column before wrapping to the right.
# With 8 sections total, 4/4 gives a balanced split. Adjust as needed.
LEFT_COLUMN_SECTIONS = 3


class TelemetryPanel(tk.Frame):
    def __init__(self, parent, telemetry):
        super().__init__(
            parent,
            highlightbackground=Theme.PANEL_EDGE,
            highlightcolor=Theme.PANEL_EDGE,
            highlightthickness=3,
        )
        self.telemetry = telemetry
        self._vars: dict[str, tk.StringVar] = {}
        self._build()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _section_frame(self, parent: tk.Frame, section_name: str, fields: list) -> None:
        """Render one section (header + rows) into *parent* and register vars."""
        tk.Label(
            parent,
            text=section_name,
            font=(Theme.FONT_MONO, Theme.FONT_SIZE_L, "bold", "underline"),
            anchor="w",
        ).pack(fill="x", padx=(10, 2), pady=(6, 0))

        for mnemonic, label, unit in fields:
            var = tk.StringVar(value="--")
            self._vars[mnemonic] = var

            row_frame = tk.Frame(parent)
            row_frame.pack(fill="x")

            tk.Label(row_frame, text=label, width=10, anchor="w").pack(
                side="left", padx=(10, 2), pady=1
            )
            tk.Label(row_frame, textvariable=var, width=8, anchor="e").pack(
                side="left", padx=2
            )
            tk.Label(row_frame, text=unit, width=4, anchor="w").pack(
                side="left", padx=2
            )

    def _build(self):
        """Place sections into two vertical sub-frames side by side."""
        left = tk.Frame(self)
        right = tk.Frame(self)
        left.grid(row=0, column=0, sticky="n")
        right.grid(row=0, column=1, sticky="n", padx=(8, 0))

        for i, (section_name, fields) in enumerate(SECTIONS):
            col_frame = left if i < LEFT_COLUMN_SECTIONS else right
            self._section_frame(col_frame, section_name, fields)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self):
        for mnemonic, var in self._vars.items():
            val = self.telemetry.get(mnemonic)
            var.set(
                f"{val:.2f}" if isinstance(val, float)
                else str(val) if val is not None
                else "--"
            )