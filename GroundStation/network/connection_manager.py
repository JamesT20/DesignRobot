import threading
import time
from core.constants import ConnState
from core.logger import get_logger
from network.ws_client import WSClient
from network.rx_thread import RXThread
from network.tx_thread import TXThread
from network.camera_thread import CameraThread

logger = get_logger("network.connection_manager")

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
        logger.info(f"Attempting to connect to {host}")
        self._set_state(ConnState.CONNECTING)
        threading.Thread(target=self._connect_loop, args=(host,), daemon=True).start()

    # disconnect the client
    def disconnect(self):
        logger.info("Disconnecting from ESP32")
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
                logger.debug("Starting RX thread")
                self._rx = RXThread(self.rx_queue, self._stop)
                logger.debug("Starting TX thread")
                self._tx = TXThread(self.tx_queue, self._stop)
                logger.debug("Starting Camera thread")
                self._cam = CameraThread(self.frame_queue, self._stop)

                self._rx.start()
                self._tx.start()
                self._cam.start()

                logger.info("Connected to ESP32 - all threads online")
                self._set_state(ConnState.CONNECTED)
                self._rx.join()  # block until rx thread dies
                logger.warning("RX thread died unexpectedly - attempting reconnection")
                self._set_state(ConnState.RECONNECTING)
            except Exception as e:
                logger.error(f"Connection error: {e}", exc_info=True)
                self._set_state(ConnState.ERROR)
            if not self._stop.is_set():
                logger.debug(f"Retrying connection in {retry_interval}s")
                time.sleep(retry_interval)

    # sett connection state
    def _set_state(self, state: ConnState):
        self.state = state
        logger.debug(f"Connection state changed to {state}")
        if self.on_state_change:
            self.on_state_change(state)