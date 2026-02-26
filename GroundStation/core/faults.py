# import time
# from core.constants import FLT, Severity
# from core.telemetry import TelemetryStore

# FAULT_DEFINITIONS = {
#     FLT.PWR_BATT_LOW:    {"severity": Severity.WARN,     "msg": "Battery voltage below warning threshold"},
#     FLT.PWR_BATT_CRIT:   {"severity": Severity.CRITICAL, "msg": "Battery voltage critical — motors stopped"},
#     FLT.PWR_OVERCURRENT: {"severity": Severity.FAULT,    "msg": "Current draw exceeds safe threshold"},
#     FLT.IMU_TILT:        {"severity": Severity.FAULT,    "msg": "Tilt angle exceeds threshold"},
#     FLT.IMU_FLIP:        {"severity": Severity.CRITICAL, "msg": "Robot has flipped"},
#     FLT.TMP_OVER:        {"severity": Severity.FAULT,    "msg": "Temperature exceeds threshold"},
#     FLT.TMP_CRIT:        {"severity": Severity.CRITICAL, "msg": "Temperature critical — motors stopped"},
#     FLT.MOT_STALL:       {"severity": Severity.WARN,     "msg": "Motor stall detected"},
#     FLT.COM_NO_TLM:      {"severity": Severity.WARN,     "msg": "No telemetry received"},
#     FLT.COM_DEAD:        {"severity": Severity.CRITICAL, "msg": "Telemetry link dead"},
# }

# class FaultManager:
#     def __init__(self, telemetry: TelemetryStore, cfg: dict):
#         self.telemetry  = telemetry
#         self.cfg        = cfg
#         self._active    = {}  # flt mnemonic → triggered timestamp

#     def check(self) -> list:
#         """Run all checks. Returns list of newly triggered fault dicts."""
#         new_faults = []
#         tlm = self.telemetry.get_all()

#         # Battery voltage
#         volt = tlm.get("PWR_BATT_VOLT")
#         if volt is not None:
#             if volt < 6.8:
#                 new_faults += self._trigger(FLT.PWR_BATT_CRIT)
#             elif volt < self.cfg.get("batt_warn_v", 7.0):
#                 new_faults += self._trigger(FLT.PWR_BATT_LOW)
#             else:
#                 self._clear(FLT.PWR_BATT_LOW)
#                 self._clear(FLT.PWR_BATT_CRIT)

#         # Tilt
#         roll  = tlm.get("IMU_ROLL_DEG")
#         pitch = tlm.get("IMU_PITCH_DEG")
#         if roll is not None and pitch is not None:
#             if abs(roll) > 75 or abs(pitch) > 75:
#                 new_faults += self._trigger(FLT.IMU_FLIP)
#             elif abs(roll) > self.cfg.get("tilt_thresh_deg", 25):
#                 new_faults += self._trigger(FLT.IMU_TILT)
#             else:
#                 self._clear(FLT.IMU_TILT)
#                 self._clear(FLT.IMU_FLIP)

#         # Telemetry staleness
#         age = self.telemetry.age_seconds()
#         if age > 1.0:
#             new_faults += self._trigger(FLT.COM_NO_TLM)
#         if age > 2.5:
#             new_faults += self._trigger(FLT.COM_DEAD)
#         if age < 0.5:
#             self._clear(FLT.COM_NO_TLM)
#             self._clear(FLT.COM_DEAD)

#         return new_faults

#     def _trigger(self, flt: str) -> list:
#         if flt not in self._active:
#             self._active[flt] = time.time()
#             return [{**FAULT_DEFINITIONS[flt], "flt": flt, "time": self._active[flt]}]
#         return []

#     def _clear(self, flt: str):
#         self._active.pop(flt, None)

#     def active_faults(self) -> dict:
#         return dict(self._active)