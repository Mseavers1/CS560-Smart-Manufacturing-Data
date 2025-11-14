'''
Test script for the client devices using MQTT to publish IMU and Camera data.
'''

import time
import numpy as np
import pandas as pd
from package.client import Client

# CONFIGURATION
BROKER_IP = "192.168.1.76"
BROKER_PORT = 1883
DEVICE_ID_IMU = "dummy_imu"
DEVICE_ID_CAMERA = "dummy_camera"

SEND_INTERVAL = 0.01
NUM_SAMPLES = 10

# DATA CREATION
def create_imu_csv(num_records: int = 1) -> str:
    """
    Generates mock IMU data with accelerometer, gyroscope,
    magnetometer, and orientation data (yaw, pitch, roll).

    Returns:
        str: CSV-formatted string (no header, num_records rows).
    """
    now = pd.Timestamp.now()
    times_ms = np.arange(num_records) * 10 + int(now.timestamp() * 1000)

    ax = np.random.uniform(-2, 2, num_records)
    ay = np.random.uniform(-2, 2, num_records)
    az = np.random.uniform(-2, 2, num_records)

    gx = np.random.uniform(-180, 180, num_records)
    gy = np.random.uniform(-180, 180, num_records)
    gz = np.random.uniform(-180, 180, num_records)

    mx = np.random.uniform(-50, 50, num_records)
    my = np.random.uniform(-50, 50, num_records)
    mz = np.random.uniform(-50, 50, num_records)

    yaw = np.random.uniform(-180, 180, num_records)
    pitch = np.random.uniform(-90, 90, num_records)
    roll = np.random.uniform(-180, 180, num_records)

    df = pd.DataFrame({
        "time_ms": times_ms,
        "ax": ax,
        "ay": ay,
        "az": az,
        "gx": gx,
        "gy": gy,
        "gz": gz,
        "mx": mx,
        "my": my,
        "mz": mz,
        "yaw": yaw,
        "pitch": pitch,
        "roll": roll
    })

    return df.to_csv(index=False, header=False).strip()

def create_camera_csv(num_records: int = 1) -> str:
    """
    Simulates camera data with frame index, marker index,
    rotation vectors (rvecx, rvecy, rvecz), and translation vectors (tvecx, tvecy, tvecz).
    Returns a CSV-formatted string (without header).
    """
    # artificial time creation, not actual NTP grab
    now = pd.Timestamp.now()
    recorded_at = np.arange(num_records) * 33 + int(now.timestamp() * 1000)          # ~30 FPS timestamps

    frame_idx = np.arange(num_records)
    marker_idx = np.random.randint(0, 10, num_records)

    # Random rotation vectors (radians) and translation vectors (cm)
    rvecx, rvecy, rvecz = np.random.uniform(-np.pi, np.pi, num_records), np.random.uniform(-np.pi, np.pi, num_records), np.random.uniform(-np.pi, np.pi, num_records)
    tvecx, tvecy, tvecz = np.random.uniform(-100, 100, num_records), np.random.uniform(-100, 100, num_records), np.random.uniform(0, 500, num_records)

    data = {
        "recorded_at": recorded_at,
        "frame_idx": frame_idx,
        "marker_idx": marker_idx,
        "rvecx": rvecx,
        "rvecy": rvecy,
        "rvecz": rvecz,
        "tvecx": tvecx,
        "tvecy": tvecy,
        "tvecz": tvecz
    }

    df = pd.DataFrame(data)
    return df.to_csv(index=False, header=False).strip()

def create_camera_csv_image_path(num_records: int = 1) -> str:
    """
    Simulates camera data with frame index, marker index,
    rotation vectors (rvecx, rvecy, rvecz), and translation vectors (tvecx, tvecy, tvecz).
    Returns a CSV-formatted string (without header).
    """
    now = pd.Timestamp.now()
    recorded_at = np.arange(num_records) * 33 + int(now.timestamp() * 1000)          # ~30 FPS timestamps

    frame_idx = np.arange(num_records)
    marker_idx = np.random.randint(0, 10, num_records)

    # Random rotation vectors (radians) and translation vectors (cm)
    rvecx, rvecy, rvecz = np.random.uniform(-np.pi, np.pi, num_records), np.random.uniform(-np.pi, np.pi, num_records), np.random.uniform(-np.pi, np.pi, num_records)
    tvecx, tvecy, tvecz = np.random.uniform(-100, 100, num_records), np.random.uniform(-100, 100, num_records), np.random.uniform(0, 500, num_records)
    path = [f"/images/frame_{i}.jpg" for i in range(num_records)]

    data = {
        "recorded_at": recorded_at,
        "frame_idx": frame_idx,
        "marker_idx": marker_idx,
        "rvecx": rvecx,
        "rvecy": rvecy,
        "rvecz": rvecz,
        "tvecx": tvecx,
        "tvecy": tvecy,
        "tvecz": tvecz,
        "image_path": path
    }

    df = pd.DataFrame(data)
    return df.to_csv(index=False, header=False).strip()

# TEST FUNCTIONS
def test_imu_client(samples, interval, id=DEVICE_ID_IMU):
    print("\n[IMU TEST] Starting IMU MQTT test...")
    imu_client = Client(
        broker_ip=BROKER_IP,
        client_type=Client.IMU,
        device_id=id,
        broker_port=BROKER_PORT
    )

    rows = create_imu_csv(samples).splitlines()

    for i, row in enumerate(rows):
        imu_client.publish(row)
        # print(f"[IMU TEST] Sent IMU data #{i}: {row}")
        time.sleep(interval)

    try:
        imu_client.disconnect()
    except Exception as e:
        print(f"[IMU ERROR] Disconnect skipped: {e}")
    print("[IMU TEST] Finished sending IMU test data.\n")

def test_camera_client(samples, interval, id=DEVICE_ID_CAMERA):
    print("[CAMERA TEST] Starting Camera MQTT test...")
    camera_client = Client(
        broker_ip=BROKER_IP,
        client_type=Client.CAMERA,
        device_id=id,
        broker_port=BROKER_PORT
    )

    rows = create_camera_csv(samples).splitlines()

    for i, row in enumerate(rows):
        camera_client.publish(row)
        # print(f"[CAMERA TEST] Sent Camera data #{i}: {row}")
        time.sleep(interval)
    try:
        camera_client.disconnect()
    except Exception as e:
        print(f"[CAMERA ERROR] Disconnect skipped: {e}")

    print("[CAMERA TEST] Finished sending Camera test data.\n")

if __name__ == "__main__":
    print(f"Using broker {BROKER_IP}:{BROKER_PORT}")
    test_imu_client(samples=NUM_SAMPLES)
    # test_camera_client(samples=NUM_SAMPLES)
