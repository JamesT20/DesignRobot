import struct
from config import PACKET_HEADER

# do a checksum
def checksum(data: bytes) -> int:
    return sum(data) & 0xFF

# converts command into a byte packet
def encode_command(command_id: int, payload: bytes) -> bytes:
    body = struct.pack('!B', command_id) + payload
    ck = checksum(body)
    return PACKET_HEADER + body + bytes([ck])