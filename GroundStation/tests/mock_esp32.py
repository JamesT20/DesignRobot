"""
Run this script to simulate an ESP32 sending telemetry.
Use instead of real hardware during development.
  python tests/mock_esp32.py
"""
import socket
import json
import time
import math

HOST = "0.0.0.0"
PORT = 8080

def generate_tlm(seq: int) -> dict:
    t = time.time()
    return {
        "type": "tlm",
        "SYS_SEQ":         seq,
        "PWR_BAT_VOLT":   7.4 + 0.4 * math.sin(t / 30),  # simulated discharge
        "PWR_BAT_CUR":      0.4 + 0.1 * math.sin(t),
        "TMP_PROBE":     27.3 + math.sin(t / 10),
    }

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"Mock ESP32 listening on {HOST}:{PORT}")

    seq = 0
    while True:
        conn, addr = server.accept()
        print(f"Client connected: {addr}")
        try:
            while True:
                tlm  = generate_tlm(seq)
                seq += 1
                conn.sendall((json.dumps(tlm) + "\n").encode())
                # Handle incoming commands
                conn.settimeout(0.1)
                try:
                    data = conn.recv(1024).decode()
                    if data:
                        msg = json.loads(data.strip())
                        print(f"CMD received: {msg.get('cmd')}")
                        ack = {"type": "ack", "cmd": msg.get("cmd"), "seq": msg.get("seq"), "status": "OK"}
                        conn.sendall((json.dumps(ack) + "\n").encode())
                except socket.timeout:
                    pass
                time.sleep(0.1)
        except Exception as e:
            print(f"Client disconnected: {e}")

if __name__ == "__main__":
    main()