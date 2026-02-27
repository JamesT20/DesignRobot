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
        # System
        "SYS_SEQ":              seq,
        "SYS_UPTIME":           int(t % 86400),
        "SYS_HEAP_FREE":        int(120000 + 5000 * math.sin(t / 60)),
        "SYS_LOOP_TIME":        int(10 + 2 * abs(math.sin(t))),
        "SYS_PACKET_NUM":       seq,
        "SYS_MODE":             "AUTO",
        # Power
        "PWR_BAT_VOLT":         round(7.4 + 0.4 * math.sin(t / 30), 3),
        "PWR_BAT_CUR":          round(0.4 + 0.1 * math.sin(t), 3),
        "PWR_MOT1_VOLT":        round(6.8 + 0.3 * math.sin(t / 20), 3),
        "PWR_MOT1_CUR":         round(0.8 + 0.5 * abs(math.sin(t / 3)), 3),
        "PWR_MOT2_VOLT":        round(6.8 + 0.3 * math.cos(t / 20), 3),
        "PWR_MOT2_CUR":         round(0.8 + 0.5 * abs(math.cos(t / 3)), 3),
        # IMU - Accelerometer (m/s²)
        "IMU_ACCEL_X":          round(0.05 * math.sin(t * 2.1), 4),
        "IMU_ACCEL_Y":          round(0.05 * math.cos(t * 1.9), 4),
        "IMU_ACCEL_Z":          round(9.81 + 0.02 * math.sin(t * 3.0), 4),
        # IMU - Gyroscope (deg/s)
        "IMU_GYRO_X":           round(0.3 * math.sin(t * 1.5), 4),
        "IMU_GYRO_Y":           round(0.3 * math.cos(t * 1.7), 4),
        "IMU_GYRO_Z":           round(0.1 * math.sin(t * 0.8), 4),
        # IMU - Magnetometer (uT)
        "IMU_MAG_X":            round(25.0 + 1.0 * math.sin(t / 15), 3),
        "IMU_MAG_Y":            round(5.0  + 1.0 * math.cos(t / 15), 3),
        "IMU_MAG_Z":            round(-42.0 + 0.5 * math.sin(t / 20), 3),
        # IMU - Orientation (degrees)
        "IMU_HEADING": round((180 + 30 * math.sin(t / 20) + 45 * math.exp(-((t % 137) - 30)**2 / 50) * math.sin(t)) % 360, 2),
        "IMU_ROLL":    round(2.0 * math.sin(t / 5)  + 60 * math.exp(-((t % 137) - 30)**2 / 50) * math.sin(t * 1.3), 3),
        "IMU_PITCH":   round(1.5 * math.cos(t / 7)  + 50 * math.exp(-((t % 137) - 30)**2 / 50) * math.cos(t * 0.9), 3),
        # Temperature
        "TMP_PROBE":            round(27.3 + math.sin(t / 10), 2),
        # Camera
        "IMG_ENDPOINT":         "http://192.168.4.1/stream",
        # Motor control
        "MOT_1_SPEED":          round(50 + 20 * math.sin(t / 8), 1),
        "MOT_1_DIR":            1 if math.sin(t / 8) >= 0 else -1,
        "MOT_1_PWM":            int(128 + 50 * math.sin(t / 8)),
        "MOT_2_SPEED":          round(50 + 20 * math.cos(t / 8), 1),
        "MOT_2_DIR":            1 if math.cos(t / 8) >= 0 else -1,
        "MOT_2_PWM":            int(128 + 50 * math.cos(t / 8)),
        # Faults (occasionally trigger for realism)
        "FLT_IMU_TILT":         abs(math.sin(t / 5)) > 0.97,
        "FLT_MOT_STALL_1":      abs(math.sin(t / 13)) > 0.99,
        "FLT_MOT_STALL_2":      abs(math.cos(t / 17)) > 0.99,
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