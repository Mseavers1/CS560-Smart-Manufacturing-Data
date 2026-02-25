"""
Robot TCP Data Flow Test Script — Full Logging + Return Stats Version
"""

import socket
import pandas as pd
import numpy as np
from datetime import datetime
import time
from logging_config import logger, colorize

# --------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------

BROKER_IP = "192.168.1.76"
BROKER_PORT = 5001

SEND_INTERVAL = 0.01
NUM_SAMPLES = 10

# --------------------------------------------------------------
# DATA CREATION
# --------------------------------------------------------------

# def create_robot_data(num_records: int = 10) -> list[str]:
#     """
#     Create robot telemetry rows (CSV strings).
#     First value sent from actual robot is a string, second is an int, rest of the values are floats
#     """
#     timestamp_str = datetime.now().strftime("%m/%d/%Y %H:%M")

#     timestamp_col = [timestamp_str] * num_records
#     int_col = np.arange(1, num_records + 1, dtype=int)

#     float_cols = {
#         f"col_{i}": np.random.uniform(-100, 100, num_records)
#         for i in range(2, 14)
#     }

#     df = pd.DataFrame({
#         "col_0": timestamp_col, 
#         "col_1": int_col,
#         **float_cols
#     })

#     return df.to_csv(index=False, header=False).strip().splitlines()

def create_robot_data(num_records: int = 10) -> list[str]:
    """
    Robot telemetry rows (CSV strings) in the exact order expected by your current robot parser:

    frame_id, ts_int, ts_str, J1, J2, J3, J4, J5, J6, X, Y, Z, W, P, R
    """
    ts_str = datetime.now().strftime("%m/%d/%Y %H:%M")
    ts_int_base = int(time.time())  # epoch seconds; change to *1000 if your robot uses ms

    df = pd.DataFrame({
        "frame_id": np.arange(1, num_records + 1, dtype=np.int64),
        "ts_int": (np.arange(num_records, dtype=np.int64) + ts_int_base),
        "ts_str": [ts_str] * num_records,

        "J1": np.random.uniform(-180, 180, num_records),
        "J2": np.random.uniform(-180, 180, num_records),
        "J3": np.random.uniform(-180, 180, num_records),
        "J4": np.random.uniform(-180, 180, num_records),
        "J5": np.random.uniform(-180, 180, num_records),
        "J6": np.random.uniform(-180, 180, num_records),

        "X": np.random.uniform(-1000, 1000, num_records),
        "Y": np.random.uniform(-1000, 1000, num_records),
        "Z": np.random.uniform(-1000, 1000, num_records),
        "W": np.random.uniform(-180, 180, num_records),
        "P": np.random.uniform(-180, 180, num_records),
        "R": np.random.uniform(-180, 180, num_records),
    })

    cols = ["frame_id", "ts_int", "ts_str",
            "J1", "J2", "J3", "J4", "J5", "J6",
            "X", "Y", "Z", "W", "P", "R"]

    return df[cols].to_csv(index=False, header=False).strip().splitlines()

# --------------------------------------------------------------
# TCP SEND TEST
# --------------------------------------------------------------

def test_robot_data(samples: int, interval: float, id: str, stop_event=None):
    """
    Sends robot telemetry over TCP.
    Compatible with master test harness.

    Returns:
        dict: {
            "samples_sent": int,
            "errors": int,
            "duration_s": float
        }
    """
    device_type = "Robot TCP Client"
    logger.info(colorize(device_type, f"[{device_type}] Starting TCP test for {id}"))

    rows = create_robot_data(samples)
    logger.debug(colorize(device_type, f"[{device_type}] {id} prepared {samples} telemetry rows"))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    errors = 0
    sent = 0
    start_time = time.perf_counter()

    try:
        logger.info(colorize(device_type, f"[{device_type}] {id} connecting to {BROKER_IP}:{BROKER_PORT}..."))
        sock.connect((BROKER_IP, BROKER_PORT))
        logger.debug(colorize(device_type, f"[{device_type}] {id} connected successfully"))  # Changed to debug

        next_send = time.perf_counter()  # Added for fixed interval timing

        for i, row in enumerate(rows, 1):  # Changed: start enumeration at 1
            if stop_event and stop_event.is_set():
                logger.info(colorize(device_type, f"[{device_type}] {id} stopping at row {i}/{samples}"))  # More consistent message
                break

            try:
                payload = row + "\n"
                sock.sendall(payload.encode("utf-8"))
                sent += 1

                logger.debug(colorize(device_type, f"[{device_type}] {id} sent row {i}/{samples}"))  # Changed format

                # Fixed interval timing (like MQTT tests)
                next_send += interval
                remaining = next_send - time.perf_counter()
                if remaining > 0:
                    time.sleep(remaining)

            except Exception as e:
                errors += 1
                logger.error(colorize(device_type, f"[{device_type}] {id} failed sending row {i}: {e}"))  # Changed format

    except Exception as e:
        logger.error(colorize(device_type, f"[{device_type}] {id} TCP connection failure: {e}"))
        errors += 1

    finally:
        logger.debug(colorize(device_type, f"[{device_type}] {id} closing socket..."))
        sock.close()
        logger.debug(colorize(device_type, f"[{device_type}] {id} socket closed"))

        duration = time.perf_counter() - start_time  # Moved inside finally block

        logger.info(colorize(device_type, 
            f"[{device_type}] {id} completed: {sent}/{samples} sent, {errors} errors, {duration:.3f}s"))

    # Standardized return dict (consistent order with MQTT tests)
    return {
        "samples_sent": sent,
        "errors": errors,
        "duration_s": duration
    }

# --------------------------------------------------------------
# MAIN
# --------------------------------------------------------------

if __name__ == "__main__":
    logger.info(colorize("Robot TCP Client", "Manual mode: sending 10 robot samples"))
    result = test_robot_data(samples=NUM_SAMPLES, interval=SEND_INTERVAL, id="manual_test")
    print(f"\nTest result: {result}")  # Added to show result