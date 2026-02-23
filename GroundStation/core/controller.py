from core.state import AppState
from net.reconnect import ReconnectManager
from net.packetizer import Packetizer
from protocol.decoder import decode_packet
from protocol.encoder import encode_command

# central information manager
class Controller:
    def __init__(self, client):
        self.client = client
        self.state = AppState()
        self.packetizer = Packetizer()
        self.reconnect = ReconnectManager(client, self._on_status)
        self.ui_callback = None  # set by UI after init

    def run(self):
        self.reconnect.connect_with_retry()
        while True:
            try:
                raw = self.client.receive()
                for packet in self.packetizer.feed(raw):
                    msg = decode_packet(packet)
                    if msg:
                        self._handle_message(msg)
            except OSError:
                self.state.connected = False
                self.reconnect.connect_with_retry()

    def _handle_message(self, msg):
        self.state.update_telemetry(msg)
        if self.ui_callback:
            self.ui_callback(msg)

    def send_command(self, command_id: int, payload: bytes = b''):
        packet = encode_command(command_id, payload)
        self.client.send(packet)

    def _on_status(self, status: str):
        self.state.connected = (status == "connected")