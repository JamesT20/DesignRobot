import threading
import time
from core.constants import ConnState
from network.ws_client import WSClient
from network.rx_thread import RXThread
from network.tx_thread import TXThread
from network.camera_thread import CameraThread

# State machine — DISCONNECTED/CONNECTING/CONNECTED/ERROR
class ConnectionManager:
    def __init__(self, rx_queue, tx_queue, frame_queue):
        self.rx_queue   = rx_queue
        self.tx_queue   = tx_queue
        self.frame_queue = frame_queue
        self.state      = ConnState.DISCONNECTED
        self._client    = None
        self._rx        = None
        self._tx        = None
        self._stop      = threading.Event()
        self.on_state_change = None  # callback for UI

    # function to start conenction thread
    def connect(self, host: str):
        self._stop.clear()
        self._set_state(ConnState.CONNECTING)
        threading.Thread(target=self._connect_loop, args=(host,), daemon=True).start()

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
    def _connect_loop(self, host: str):
        retry_interval = 3
        while not self._stop.is_set():
            try:

                self._rx = RXThread(self.rx_queue, self._stop)
                print('rx online')
                self._tx = TXThread(self.tx_queue, self._stop)
                print('tx online')
                self._cam = CameraThread(self.frame_queue, self._stop)
                print('cam online')

                self._rx.start()
                self._tx.start()
                self._cam.start()

                self._set_state(ConnState.CONNECTED)
                self._rx.join()  # block until rx thread dies
                self._set_state(ConnState.RECONNECTING)
            except Exception as e:
                print(e)
                self._set_state(ConnState.ERROR)
            if not self._stop.is_set():
                time.sleep(retry_interval)

    # sett connection state
    def _set_state(self, state: ConnState):
        self.state = state
        if self.on_state_change:
            self.on_state_change(state)