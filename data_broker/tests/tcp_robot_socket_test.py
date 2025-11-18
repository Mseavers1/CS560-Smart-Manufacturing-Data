"""
Robot TCP Data Flow Test Script

Simulates sending robot telemetry data to the Data Broker over TCP.

Robot Data Format:
    14 columns total
        [0] - empty
        [1] - integer
        [2-13] - floats 

TCP Socket Details:
    IP: 192.168.1.76
    PORT: 5001
"""

import socket
import pandas as pd
import numpy as np
import time

BROKER_IP = "192.168.1.76"
BROKER_PORT = 5001
NUM_RECORDS = 10    
SEND_INTERVAL = 0.2

# DATA CREATION
def create_robot_data(num_records: int = 10) -> pd.DataFrame:
    """
    Create a DataFrame that simulates robot telemetry.
    Format: [empty, int, float x 12] = 14 columns total.
    """

    empty_col = [""] * num_records
    int_col = np.arange(1, num_records + 1, dtype=int)
    float_cols = {
        f"col_{i}": np.random.uniform(-100, 100, num_records)
        for i in range(2, 14)
    }

    df = pd.DataFrame({
        "col_0": empty_col,
        "col_1": int_col,
        **float_cols
    })

    return df

# DATA SENDING
def test_robot_data(samples, id="ROBOT", interval=SEND_INTERVAL):
    """
    Sends each row of the DataFrame as a CSV string over TCP.
    """
    df = create_robot_data(samples)
    print(f"[ROBOT TEST] Connecting to Data Broker at {BROKER_IP}:{BROKER_PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((BROKER_IP, BROKER_PORT))
        print("[ROBOT TEST] Connected successfully.")
        # print(f"[INFO] Sending {len(df)} data points...")

        for i, row in df.iterrows():
            csv_line = ",".join(map(str, row.values)) + "\n"
            sock.sendall(csv_line.encode("utf-8"))
            # print(f"[SEND] {csv_line.strip()}")
            time.sleep(interval)

        print("[ROBOT TEST] Finished sending data.")

    except Exception as e:
        print(f"[ROBOT ERROR] Connection or send failed: {e}")

    finally:
        print("[ROBOT TEST] Closing socket...")
        sock.close()
        print("[ROBOT TEST] Socket closed.")

if __name__ == "__main__":
    samples = NUM_RECORDS
    test_robot_data(samples)