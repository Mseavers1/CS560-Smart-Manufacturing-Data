#!/usr/bin/env python3
"""
full_system_tester_v2.py

Unified master test harness for running IMU, Camera, and Robot TCP testers concurrently.
Uses the shared logger defined in logging_config.py

KNOWN ISSUES
Since this uses python, we are limited by the GIL, therefore heavier test will naturally lag more
Could update python or move to another lang for the future.
"""

from logging_config import logger, colorize
import os
import threading
import queue
import csv
import time
import sys
from typing import Callable
import pandas as pd

#  edit these imports to the new v2 scripts
from mqtt_tester_v2 import test_imu_client, test_camera_client
from tcp_robot_test_v2 import test_robot_data


# -----------------------------
# Test Configuration
# -----------------------------
IMU_DEVICE_CNT = 1
CAM_DEVICE_CNT = 1
ROBOT_DEVICE_CNT = 1

IMU_SAMPLES = 1000
CAM_SAMPLES = 1000
ROBOT_SAMPLES = 1000

# interval = 0.001 s (1000 Hz)
IMU_INT = 0.1
CAM_INT = 0.1
ROBOT_INT = 0.1

CLIENT_FUNCTIONS = {
    "Camera Client": test_camera_client,
    "IMU Client": test_imu_client,
    "Robot TCP Client": test_robot_data,
}

DEVICE_COUNTS = {
    "Camera Client": CAM_DEVICE_CNT,
    "IMU Client": IMU_DEVICE_CNT,
    "Robot TCP Client": ROBOT_DEVICE_CNT,
}

DEVICE_SAMPLES = {
    "Camera Client": CAM_SAMPLES,
    "IMU Client": IMU_SAMPLES,
    "Robot TCP Client": ROBOT_SAMPLES,
}

DEVICE_INTERVALS = {
    "Camera Client": CAM_INT,
    "IMU Client": IMU_INT,
    "Robot TCP Client": ROBOT_INT,
}

# -----------------------------
# Create file path for saved results
# -----------------------------
def generate_results_path(
    imu_runs, imu_samples, imu_int,
    cam_runs, cam_samples, cam_int,
    robot_runs, robot_samples, robot_int,
    base_dir="test_results"
):
    # Create directory if not exists
    os.makedirs(base_dir, exist_ok=True)

    # Base filename without index
    base_name = f"dev_imu{imu_runs}sam{imu_samples}int{imu_int}dev_cam{cam_runs}sam{cam_samples}int{cam_int}dev_robot{robot_runs}sam{robot_samples}int{robot_int}"

    # Find next available index
    index = 1
    while True:
        filename = f"{base_name}_test{index}.csv"
        full_path = os.path.join(base_dir, filename)
        if not os.path.exists(full_path):
            return full_path
        index += 1

def save_results(data, filename="results.csv"):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    logger.info(f"Saved results to {filename}")

# -----------------------------
# Device Thread Wrapper
# -----------------------------
def device_wrapper(
    device_name: str,
    func: Callable,
    samples: int,
    interval: float,
    device_id: str,
    results_q: queue.Queue,
    stop_event: threading.Event,
):
    """
    Wraps execution of a device test function with:
      - timing
      - unified logging
      - result collection
    Now captures actual return values from test functions.
    """
    logger.info(colorize(device_name, f"[{device_name}] {device_id} starting test..."))

    start = time.perf_counter()

    result = {
        "device_id": device_id,
        "device_type": device_name,
        "samples_requested": samples,
        "samples_completed": 0,
        "samples_sent": 0,
        "errors": 0,
        "duration_s": None,
        "avg_rate_hz": None,
        "success_rate": None,
        "error": None,
    }

    test_result = None

    try:
        # Call test function and capture return value
        test_result = func(samples, interval, device_id, stop_event)

        if stop_event.is_set():
            logger.info(colorize(device_name, f"[{device_name}] {device_id} stopped early."))

    except Exception as e:
        logger.exception(colorize(device_name, f"[{device_name}] {device_id} encountered an exception"))
        result["error"] = str(e)

    finally:
        end = time.perf_counter()
        duration = end - start

        result["duration_s"] = duration

        # Extract actual metrics from test function return value
        if test_result and isinstance(test_result, dict):
            result["samples_sent"] = test_result.get("samples_sent", 0)
            result["errors"] = test_result.get("errors", 0)
            result["samples_completed"] = result["samples_sent"]
        else:
            # Fallback if test function didn't return proper dict
            result["samples_completed"] = samples if not result["error"] else 0
            result["samples_sent"] = result["samples_completed"]

        # Calculate derived metrics
        result["avg_rate_hz"] = (
            (result["samples_sent"] / duration) if duration > 0 else 0.0
        )
        result["success_rate"] = (
            ((result["samples_sent"] / samples) * 100) if samples > 0 else 0.0
        )

        results_q.put(result)

        logger.info(
            colorize(
                device_name,
                f"[{device_name}] {device_id} finished: "
                f"{result['samples_sent']}/{result['samples_requested']} samples "
                f"({result['errors']} errors) in {duration:.3f}s "
                f"({result['avg_rate_hz']:.3f} Hz, {result['success_rate']:.1f}% success)",
            )
        )

# -----------------------------
# Run All Tests
# -----------------------------
def run_all_tests(export_csv: str | None = None):
    stop_event = threading.Event()
    results_q = queue.Queue()
    threads = []

    logger.info("[MAIN] Starting system test harness...")
    logger.info(f"[MAIN] Configuration: IMU={IMU_DEVICE_CNT}, CAM={CAM_DEVICE_CNT}, ROBOT={ROBOT_DEVICE_CNT}")

    # Start test threads
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
                args=(name, func, samples, interval, device_id, results_q, stop_event),
                daemon=False,
            )
            threads.append(t)
            t.start()

            logger.info(colorize(name, f"[MAIN] Started {thread_name} with ID '{device_id}'"))

    # Wait for completion or Ctrl+C
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.warning("[MAIN] KeyboardInterrupt received — stopping all tests...")
        stop_event.set()
        for t in threads:
            t.join(timeout=2.0)

    # Collect results
    results = []
    while not results_q.empty():
        results.append(results_q.get())

    print("\n" + "=" * 80)
    print(" SYSTEM TEST SUMMARY")
    print("=" * 80 + "\n")

    total_sent = 0
    total_requested = 0
    total_errors = 0
    failed_tests = []

    for r in results:
        print(f"Device: {r['device_id']}")
        print(f"  Type:           {r['device_type']}")
        print(f"  Requested:      {r['samples_requested']}")
        print(f"  Sent:           {r['samples_sent']}")
        print(f"  Errors:         {r['errors']}")
        print(f"  Duration:       {r['duration_s']:.3f}s")
        print(f"  Avg rate:       {r['avg_rate_hz']:.3f} Hz")
        print(f"  Success rate:   {r['success_rate']:.1f}%")
        if r["error"]:
            print(f"  ERROR:          {r['error']}")
            failed_tests.append(r['device_id'])
        print()

        total_sent += r['samples_sent']
        total_requested += r['samples_requested']
        total_errors += r['errors']

    print("-" * 80)
    print("OVERALL STATISTICS:")
    print(f"  Total Requested:    {total_requested}")
    print(f"  Total Sent:         {total_sent}")
    print(f"  Total Errors:       {total_errors}")
    print(f"  System Success:     {(total_sent / total_requested * 100):.1f}%" if total_requested > 0 else "N/A")
    print(f"  Failed Tests:       {len(failed_tests)}")
    if failed_tests:
        print(f"  Failed Device IDs:  {', '.join(failed_tests)}")
    print("-" * 80)

    system_status = "PASS" if total_errors == 0 and not failed_tests else "FAIL"
    print(f"\nSYSTEM STATUS: {system_status}")
    print("=" * 80 + "\n")


    output_path = generate_results_path(
        imu_runs=IMU_DEVICE_CNT,
        imu_samples=IMU_SAMPLES,
        imu_int=IMU_INT,
        cam_runs=CAM_DEVICE_CNT,
        cam_samples=CAM_SAMPLES,
        cam_int=CAM_INT,
        robot_runs=ROBOT_DEVICE_CNT,
        robot_samples=ROBOT_SAMPLES,
        robot_int=ROBOT_INT,
    )

    save_results(results, output_path)

    return results
# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    run_all_tests()