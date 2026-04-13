import threading
import queue
from core.protocol import serialize

# Transmit thread — reads tx_queue, sends to socket
class TXThread(threading.Thread):
    def __init__(self, tx_queue, stop_event):
        super().__init__(daemon=True)
        self.tx_queue   = tx_queue
        self.stop_event = stop_event

    # runs on thread creation
    def run(self):
        while not self.stop_event.is_set():
            #print('tx thread running')
            try:
                msg  = self.tx_queue.get(timeout=0.1)
                data = serialize(msg)
                self.client.send(data)
            except queue.Empty:
                continue
            except Exception as e:
                print(e)
                break