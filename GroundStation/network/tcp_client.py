import socket

class TCPClient:
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.host    = host
        self.port    = port
        self.timeout = timeout
        self._sock   = None
        self._buffer = ""

    # connects to the host
    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._sock.connect((self.host, self.port))
        self._buffer = ""

    # disconnect from the socket
    def disconnect(self):
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    # send data to socket
    def send(self, data: bytes):
        if self._sock:
            self._sock.sendall(data)

    # recieve everything up until a delimiter, chunks of data will be combined with the buffer
    def receive_line(self) -> str:
        while "\n" not in self._buffer:
            chunk = self._sock.recv(4096).decode("utf-8")
            if not chunk:
                raise ConnectionError("Socket closed by remote")
            self._buffer += chunk
        line, self._buffer = self._buffer.split("\n", 1)
        return line

    # class property storing if it is connected
    @property
    def connected(self) -> bool:
        return self._sock is not None