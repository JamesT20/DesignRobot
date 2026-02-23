import struct
from protocol.message_types import Telemetry

# do a checksum
def checksum(data: bytes) -> int:
    return sum(data) & 0xFF

# decode a packet back into the telemetry
def decode_packet(packet: bytes):
    if len(packet) < 4:
        return None
    body, ck = packet[:-1], packet[-1]
    if checksum(body) != ck:
        return None  # invalid
    msg_type = body[0]
    if msg_type == 0x01:
        ts, temp, volts, status = struct.unpack('!fddf', body[1:])
        return Telemetry(ts, temp, volts, status)
    return None