import threading
import time
from core.constants import ConnState
from network.tcp_client import TCPClient
from network.rx_thread import RXThread
from network.tx_thread import TXThread

class ConnectionManager:
    def __init__(self, rx_queue, tx_queue):
        self.rx_queue   = rx_queue
        self.tx_queue   = tx_queue
        self.state      = ConnState.DISCONNECTED
        self._client    = None
        self._rx        = None
        self._tx        = None
        self._stop      = threading.Event()
        self.on_state_change = None  # callback for UI

    # function to start conenction thread
    def connect(self, host: str, port: int):
        self._stop.clear()
        self._set_state(ConnState.CONNECTING)
        threading.Thread(target=self._connect_loop, args=(host, port), daemon=True).start()

    # disconnect the client
    def disconnect(self):
        self._stop.set()
        if self._client:
            self._client.disconnect()
        self._set_state(ConnState.DISCONNECTED)

    # put into the tx queue
    def send(self, data: bytes):
        self.tx_queue.put(data)

    # connect loop to try and connect
    def _connect_loop(self, host, port):
        retry_interval = 3
        while not self._stop.is_set():
            try:
                self._client = TCPClient(host, port)
                self._client.connect()
                self._rx = RXThread(self._client, self.rx_queue, self._stop)
                self._tx = TXThread(self._client, self.tx_queue, self._stop)
                self._rx.start()
                self._tx.start()
                self._set_state(ConnState.CONNECTED)
                self._rx.join()  # block until rx thread dies
                self._set_state(ConnState.RECONNECTING)
            except Exception as e:
                self._set_state(ConnState.ERROR)
            if not self._stop.is_set():
                time.sleep(retry_interval)

    # sett connection state
    def _set_state(self, state: ConnState):
        self.state = state
        if self.on_state_change:
            self.on_state_change(state)