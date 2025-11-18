import threading
import time

from mqtt_publish_tester import test_imu_client, test_camera_client
from tcp_robot_socket_test import test_robot_data

<<<<<<< HEAD
# SET SAMPLE SIZE AND SEND_INTERVAL
SAMPLES = 1000
SEND_INTERVAL = 0.001
=======
>>>>>>> d2b492651ea3f6620ae2ddf5c5aeda753bb913ec

# -----------------------------
# Test Configuration
# -----------------------------

IMU_DEVICE_CNT = 1
CAM_DEVICE_CNT = 1
ROBOT_DEVICE_CNT = 1

IMU_SAMPLES = 1000
CAM_SAMPLES = 1000
ROBOT_SAMPLES = 1000

IMU_INT = 0.1
CAM_INT = 0.1
ROBOT_INT = 0.1

RESULT_LOCK = threading.Lock()

CLIENT_FUNCTIONS = {
    "Camera Client": test_camera_client,
    "IMU Client": test_imu_client,
    "Robot TCP Client": test_robot_data
}

<<<<<<< HEAD
def run_all_tests(samples, interval):
=======
DEVICE_COUNTS = {
    "Camera Client": CAM_DEVICE_CNT,
    "IMU Client": IMU_DEVICE_CNT,
    "Robot TCP Client": ROBOT_DEVICE_CNT
}

DEVICE_SAMPLES = {
    "Camera Client": CAM_SAMPLES,
    "IMU Client": IMU_SAMPLES,
    "Robot TCP Client": ROBOT_SAMPLES
}

DEVICE_INTERVALS = {
    "Camera Client": CAM_INT,
    "IMU Client": IMU_INT,
    "Robot TCP Client": ROBOT_INT
}

class Colors:
    IMU = "\033[94m"      # Blue
    CAM = "\033[93m"      # Yellow
    ROBOT = "\033[92m"    # Green
    END = "\033[0m"


def get_color(name):
    if "Camera" in name:
        return Colors.CAM
    if "IMU" in name:
        return Colors.IMU
    if "Robot" in name:
        return Colors.ROBOT
    return Colors.END


# -----------------------------
# Thread wrapper for timing + logging
# -----------------------------
def device_wrapper(device_name, func, samples, interval, device_id, results_store):
    color = get_color(device_name)

    print(f"{color}[{device_name}] '{device_id}' starting test...{Colors.END}")

    start_time = time.time()

    # Run the actual MQTT/TCP client function
    # IMPORTANT: Your client must accept (samples, interval, device_id)
    func(samples, interval, device_id)

    end_time = time.time()
    duration = end_time - start_time
    rate = samples / duration if duration > 0 else 0

    # Store results for summary later
    with RESULT_LOCK:
        results_store[device_id] = {
            "device_type": device_name,
            "samples": samples,
            "duration": duration,
            "avg_rate": rate
        }

    print(f"{color}[{device_name}] '{device_id}' finished: "
          f"{samples} samples in {duration:.2f}s → {rate:.2f} Hz avg{Colors.END}")


# -----------------------------
# Run All Tests
# -----------------------------
def run_all_tests():
>>>>>>> d2b492651ea3f6620ae2ddf5c5aeda753bb913ec
    threads = []
    results_store = {}

    for name, count in DEVICE_COUNTS.items():
        func = CLIENT_FUNCTIONS[name]
        samples = DEVICE_SAMPLES[name]
        interval = DEVICE_INTERVALS[name]

        for i in range(count):

            if "Camera" in name:
                device_id = f"dummy_camera_{i+1}"
            elif "IMU" in name:
                device_id = f"dummy_imu_{i+1}"
            elif "Robot" in name:
                device_id = f"dummy_robot_{i+1}"
            else:
                device_id = f"dummy_device_{i+1}"

            thread_name = f"{name} #{i+1}"

            t = threading.Thread(
                target=device_wrapper,
                name=thread_name,
<<<<<<< HEAD
                daemon=True,
                args=(samples, device_id, interval)
=======
                args=(name, func, samples, interval, device_id, results_store)
>>>>>>> d2b492651ea3f6620ae2ddf5c5aeda753bb913ec
            )

            threads.append(t)
            t.start()
            print(f"[MAIN] Started {thread_name} with ID '{device_id}'")

    # Wait for threads
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("[MAIN] Interrupted, exiting early...")

    print("\n=====================")
    print("   SYSTEM SUMMARY")
    print("=====================\n")

    for dev_id, stats in results_store.items():
        print(f"Device: {dev_id}")
        print(f"  Type:       {stats['device_type']}")
        print(f"  Samples:    {stats['samples']}")
        print(f"  Duration:   {stats['duration']:.2f}s")
        print(f"  Avg rate:   {stats['avg_rate']:.2f} Hz\n")

    print("SYSTEM STATUS: COMPLETE")


if __name__ == "__main__":
<<<<<<< HEAD
    run_all_tests(samples=SAMPLES, interval=SEND_INTERVAL)
=======
    run_all_tests()
>>>>>>> d2b492651ea3f6620ae2ddf5c5aeda753bb913ec
