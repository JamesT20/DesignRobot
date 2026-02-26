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