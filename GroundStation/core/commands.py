import itertools

# Auto-incrementing sequence number (client-side tracking only)
_seq = itertools.count(1)


def _cmd(cmd: str, **kwargs) -> dict:
    """Build a single ESP32 command dict."""
    entry = {"cmd": cmd}
    entry.update(kwargs)
    return entry


def _sequence(*cmds: dict) -> list:
    """
    Wrap one or more command dicts into a TX-ready message.
    The list is what gets POST-ed to /cmd as a JSON array.
    """
    return {
        "endpoint": "/cmd",
        "seq":      next(_seq),
        "commands": list(cmds),
    }


# ── Single-command helpers ────────────────────────────────────────────────────

def set_motor_dir(left_dir: int, right_dir: int) -> dict:
    """
    Set both motors to a direction immediately.
    left_dir / right_dir: 1 = forward, -1 = reverse, 0 = brake
    """
    left_dir  = max(-1, min(1, left_dir))
    right_dir = max(-1, min(1, right_dir))
    return _sequence(
        _cmd("CMD_MOT_SET_DIR", left_dir=left_dir, right_dir=right_dir)
    )


def stop() -> dict:
    """Brake both motors via the command queue."""
    return _sequence(
        _cmd("CMD_MOT_STOP")
    )


def estop() -> dict:
    """
    Emergency stop — hits /cmd/stop directly, bypasses and clears the queue.
    The TX thread routes this to the /cmd/stop endpoint.
    """
    return {"endpoint": "/cmd/stop", "seq": next(_seq)}


def wait(ms: int) -> dict:
    """Block the command queue for the given number of milliseconds."""
    ms = max(0, ms)
    return _sequence(
        _cmd("CMD_SYS_WAIT", ms=ms)
    )


def reboot() -> dict:
    """Reboot the ESP32."""
    return _sequence(
        _cmd("CMD_SYS_REBOOT")
    )


def clear_faults() -> dict:
    """Clear all fault flags on the ESP32."""
    return _sequence(
        _cmd("CMD_SYS_CLEAR_FAULTS")
    )


# ── Compound sequence helpers ─────────────────────────────────────────────────

def drive(left_dir: int, right_dir: int, duration_ms: int) -> dict:
    """
    Drive for a fixed duration then brake.
    Sends as a single 3-command sequence: SET_DIR → WAIT → STOP
    """
    left_dir  = max(-1, min(1, left_dir))
    right_dir = max(-1, min(1, right_dir))
    duration_ms = max(0, duration_ms)
    return _sequence(
        _cmd("CMD_MOT_SET_DIR", left_dir=left_dir, right_dir=right_dir),
        _cmd("CMD_SYS_WAIT",    ms=duration_ms),
        _cmd("CMD_MOT_STOP"),
    )


def turn(direction: str, duration_ms: int) -> dict:
    """
    Convenience turn: 'left' spins motors in opposite directions, 'right' mirrors.
    """
    duration_ms = max(0, duration_ms)
    if direction == "left":
        l, r = -1, 1
    elif direction == "right":
        l, r = 1, -1
    else:
        raise ValueError(f"direction must be 'left' or 'right', got {direction!r}")
    return drive(l, r, duration_ms)


def sequence(*cmds: dict) -> dict:
    """
    Combine multiple single-command helpers into one POST.
    Usage: sequence(
               set_motor_dir(1, 1),   # these will be flattened
               wait(500),
               stop()
           )
    Note: only works with non-estop commands (those with endpoint=/cmd).
    """
    flat = []
    for msg in cmds:
        if msg.get("endpoint") != "/cmd":
            raise ValueError("sequence() cannot include estop commands")
        flat.extend(msg["commands"])
    return {"endpoint": "/cmd", "seq": next(_seq), "commands": flat}