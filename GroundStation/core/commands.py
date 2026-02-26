import itertools
from core.constants import CMD

_seq = itertools.count(1)  # auto-incrementing sequence number

def _build(cmd: str, params: dict = {}) -> dict:
    return {
        "type":   "cmd",
        "cmd":    cmd,
        "seq":    next(_seq),
        "params": params
    }

def set_motor_speed(left_pct: int, right_pct: int) -> dict:
    left_pct  = max(-100, min(100, left_pct))
    right_pct = max(-100, min(100, right_pct))
    return _build(CMD.MOT_SET_SPEED, {"left_pct": left_pct, "right_pct": right_pct})

def estop() -> dict:
    return _build(CMD.MOT_ESTOP)

def set_tlm_rate(interval_ms: int) -> dict:
    interval_ms = max(50, min(5000, interval_ms))
    return _build(CMD.CFG_SET_TLM_RATE, {"interval_ms": interval_ms})

def reboot() -> dict:
    return _build(CMD.SYS_REBOOT)

def ping() -> dict:
    return _build(CMD.SYS_PING)

def start_stream() -> dict:
    return _build(CMD.CAM_STREAM_START)