'''
testing the combined system data flow
sends mqtt and tcp data to simulate all clients sending at once
'''

import threading, time
from mqtt_publish_tester import test_imu_client, test_camera_client
from tcp_robot_socket_test import test_robot_data


SAMPLES = 10

def run_all_tests(SAMPLES):
    threads = []

    tests = [
        ("Camera Client", test_camera_client),
        ("IMU Client", test_imu_client),
        ("Robot TCP Client", test_robot_data)
    ]

    for name, func in tests:
        t = threading.Thread(target=func, name=name, daemon=True, args=(SAMPLES,))
        threads.append(t)
        t.start()
        print(f"[MAIN] Started {name} thread")

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        print("[MAIN] Interrupted! Exiting...")
    print("[MAIN] All tests completed")

if __name__ == "__main__":
    run_all_tests(SAMPLES) 