import threading

class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self.connected = False
        self.latest_telemetry = None
        self.last_command_time = {}
        self.error_flags = []

    def update_telemetry(self, telemetry):
        with self._lock:
            self.latest_telemetry = telemetry

    def get_telemetry(self):
        with self._lock:
            return self.latest_telemetry