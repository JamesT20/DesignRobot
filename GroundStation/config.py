# esp32 ip and port
HOST = "192.168.1.100"
PORT = 9000

# when to reconnect and how many times
RECONNECT_INTERVAL = 5.0
MAX_RECONNECT_ATTEMPTS = 10

# seconds between updates
TELEMETRY_RATE_LIMIT = 0.1
PACKET_HEADER = b'\xAA\xBB'
BUFFER_SIZE = 4096