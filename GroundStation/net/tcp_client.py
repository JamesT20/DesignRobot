import socket

# this actually connects to the esp32

class TCPClient:

    # set up host and port
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    # function to connect to the port
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    # function to send data to the port
    def send(self, data: bytes):
        self.sock.sendall(data)

    # function to recieve data from the port
    def receive(self, size=4096) -> bytes:
        return self.sock.recv(size)

    # function to disconnect from the port
    def disconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None