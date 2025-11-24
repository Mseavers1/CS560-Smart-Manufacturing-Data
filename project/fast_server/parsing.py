from typing import Any

# Helper method to parse CAMERA messages
def parse_camera_message(topic, payload) -> dict[str, Any]:

    # Get device and topic info -- Topic should be 'IMU/<device_ID>' or similar
    parts = topic.split("/")

    # If more or less parts, raise an error
    if len(parts) != 2:
        raise ValueError(f"Invalid topic: {topic!r}")

    device_label = parts[1]

    # Messages should be in CSV format
    msg = [part.strip() for part in payload.decode().split(",")]

    # If less parts, raise an error
    if len(msg) < 9:
        raise ValueError(f"Expected at least 9 fields, got {len(msg)}")

    return {
            "device_label": device_label,
            "recorded_at": float(msg[0]),
            "frame_idx": int(msg[1]),
            "marker_idx": int(msg[2]),
            "rvec_x": float(msg[3]),
            "rvec_y": float(msg[4]),
            "rvec_z": float(msg[5]),
            "tvec_x": float(msg[6]),
            "tvec_y": float(msg[7]),
            "tvec_z": float(msg[8]),
            "image_path": "" # TODO - Remove image path from DB
    }

# Helper method to parse IMU messages
def parse_imu_message(topic, payload) -> dict[str, Any]:

    # Get device and topic info -- Topic should be 'IMU/<device_ID>' or similar
    parts = topic.split("/")

    # If more or less parts, raise an error
    if len(parts) != 2:
        raise ValueError(f"Invalid topic: {topic!r}")

    device_label = parts[1]

    # Messages should be in CSV format
    msg = [part.strip() for part in payload.decode().split(",")]

    # If less parts, raise an error
    if len(msg) < 13:
        raise ValueError(f"Expected at least 13 fields, got {len(msg)}")

    return {
        "device_label": device_label,
        "recorded_at": float(msg[0]),
        "accel_x": float(msg[1]),
        "accel_y": float(msg[2]),
        "accel_z": float(msg[3]),
        "gyro_x": float(msg[4]),
        "gyro_y": float(msg[5]),
        "gyro_z": float(msg[6]),
        "mag_x": float(msg[7]),
        "mag_y": float(msg[8]),
        "mag_z": float(msg[9]),
        "yaw": float(msg[10]),
        "pitch": float(msg[11]),
        "roll": float(msg[12]),
    }