import threading
import time
from core.constants import TLM

# this class is used by threads to get set current tlm values
class TelemetryStore:

    def __init__(self):
        self._lock  = threading.Lock()
        self._store = {key: None for key in vars(TLM) if not key.startswith("_")}
        self._last_updated = None

    # update key/value pair
    def update(self, data: dict):
        with self._lock:
            for key, value in data.items():
                if key in self._store:
                    self._store[key] = value
            self._last_updated = time.time()

    # get tlm value based off given mnemonic
    def get(self, mnemonic: str):
        with self._lock:
            return self._store.get(mnemonic)

    # get full tlm dict
    def get_all(self) -> dict:
        with self._lock:
            return dict(self._store)

    # get time since last updated
    def age_seconds(self) -> float:
        if self._last_updated is None:
            return float("inf")
        return time.time() - self._last_updated