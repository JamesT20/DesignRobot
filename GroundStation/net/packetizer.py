HEADER = b'\xAA\xBB'
PACKET_SIZE = 64  # fixed-size example

# used to split bytes into packets
class Packetizer:
    def __init__(self):
        self.buffer = b''

    # converts a feed of data into packets
    def feed(self, data: bytes) -> list:
        self.buffer += data
        packets = []
        while len(self.buffer) >= PACKET_SIZE:
            idx = self.buffer.find(HEADER)
            if idx == -1:
                self.buffer = b''
                break
            if idx + PACKET_SIZE <= len(self.buffer):
                packets.append(self.buffer[idx:idx + PACKET_SIZE])
                self.buffer = self.buffer[idx + PACKET_SIZE:]
            else:
                break
        return packets