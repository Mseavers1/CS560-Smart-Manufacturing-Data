import threading, time
from mqtt_publish_tester import test_imu_client, test_camera_client
from tcp_robot_socket_test import test_robot_data

SAMPLES = 1000

# How many of each simulated device to run
DEVICE_COUNTS = {
    "Camera Client": 1,  
    "IMU Client": 1,     
    "Robot TCP Client": 1 
}

# Map client types to functions
CLIENT_FUNCTIONS = {
    "Camera Client": test_camera_client,
    "IMU Client": test_imu_client,
    "Robot TCP Client": test_robot_data
}

def run_all_tests(samples):
    threads = []

    for name, count in DEVICE_COUNTS.items():
        func = CLIENT_FUNCTIONS[name]
        for i in range(count):
            # Create a unique device ID (e.g. dummy_camera_1)
            if "Camera" in name:
                device_id = f"dummy_camera_{i+1}"
            elif "IMU" in name:
                device_id = f"dummy_imu_{i+1}"
            elif "Robot" in name:
                device_id = f"dummy_robot_{i+1}"
            else:
                device_id = f"dummy_device_{i+1}"

            # Start each client in its own thread
            thread_name = f"{name} #{i+1}"
            t = threading.Thread(
                target=func,
                name=thread_name,
                daemon=True,
                args=(samples, device_id)  # <-- pass device_id here
            )
            threads.append(t)
            t.start()
            print(f"[MAIN] Started {thread_name} with ID '{device_id}'")

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("[MAIN] Interrupted! Exiting...")
    print("[MAIN] All tests completed")

if __name__ == "__main__":
    run_all_tests(SAMPLES)
