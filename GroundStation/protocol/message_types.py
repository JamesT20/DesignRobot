from dataclasses import dataclass

# Telemetry message
@dataclass
class Telemetry:
    timestamp: float
    temperature: float
    voltage: float
    status_code: int

@dataclass
class CommandAck:
    command_id: int
    success: bool

@dataclass
class ErrorReport:
    code: int
    message: str

@dataclass
class Heartbeat:
    timestamp: float