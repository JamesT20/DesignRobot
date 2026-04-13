import json

DELIMITER = "\n"

# serialize the json byte string
def serialize(msg: dict) -> bytes:
    return (json.dumps(msg) + DELIMITER).encode("utf-8")

# deserialize a json string into a dict
def deserialize(raw: str) -> dict:
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return None

# check if this a valid message
def is_valid(msg: dict) -> bool:
    return isinstance(msg, dict) and "type" in msg

def msg_type(msg: dict) -> str:
    return msg.get("type", "unknown")


# ──────────────────────────────────────────────────────────────────────────
# Protocol Message Types
# ──────────────────────────────────────────────────────────────────────────
# 
# "tlm" — Telemetry (DUI → GUI)
#   Contains sensor readings, motor states, power stats, etc.
#   Sent periodically via GET /tlm endpoint
#
# "fault" — Fault Event (DUI → GUI)
#   Indicates a fault has been triggered or cleared
#   Fields: flt (fault code), severity, message, timestamp
#
# "ack" — Command Acknowledgment (DUI → GUI)
#   Response to command sent. Optional in current implementation.
#   Fields: cmd (command name), status (OK|ERR), seq (sequence number)
#
# "log" — Logging Message (DUI → GUI) ✨ NEW
#   DUI subsystem sends structured log messages for debugging/monitoring
#   Fields: 
#     - timestamp: int (milliseconds since DUI boot)
#     - level: str (INFO, DEBUG, WARN, ERROR)
#     - source: str (subsystem name: motors, imu, power, camera, etc.)
#     - message: str (human-readable log message)
#     - context: dict, optional (additional metadata for debugging)
#   Example:
#     {
#       "type": "log",
#       "timestamp": 156234,
#       "level": "INFO",
#       "source": "motors",
#       "message": "Motor A initialized",
#       "context": {"motor_id": 1, "control_mode": "PWM"}
#     }
#   GUI Routes to: LogPanel with prefix "[{source}] {message}"
#
# "pong" — Heartbeat Response (DUI → GUI)
#   Response to ping/heartbeat requests. Currently ignored by GUI.
#