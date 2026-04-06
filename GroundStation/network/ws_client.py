import requests

#Raw WS socket management — connect, send, recv, reconnect
class WSClient:
    def __init__(self, host: str, timeout: float = 5.0):
        self.host    = host
        self.timeout = timeout
        self._session   = None
        self._buffer = ""

    # connects to the host
    def connect(self):
        self._session = requests.Session()

    # disconnect from the session
    def disconnect(self):
        self._session.close()

    # send data to socket
    def send(self, data: bytes):
        if self._sock:
            self._sock.sendall(data)

    # recieve everything up until a delimiter, chunks of data will be combined with the buffer
    def receive_tlm(self) -> str:
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