#!/usr/bin/env python3
"""
full_system_tester_v3.py

Rewritten from scratch to ensure:
- Device increments work every step
- Interval decrements work every step
- Stress test is deterministic and debuggable
- No global mutation of configuration
"""

import os
import sys
import time
import queue
import threading
import pandas as pd
from typing import Callable

from logging_config import logger, colorize
from mqtt_tester_v2 import test_imu_client, test_camera_client
from tcp_robot_test_v2 import test_robot_data


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

CLIENT_FUNCTIONS = {
    "IMU": test_imu_client,
    "CAMERA": test_camera_client,
    "ROBOT": test_robot_data,
}

DEVICE_ID_PREFIX = {
    "IMU": "dummy_imu",
    "CAMERA": "dummy_camera",
    "ROBOT": "dummy_robot",
}

DEFAULT_DEVICE_SAMPLES = {
    "IMU": 100,
    "CAMERA": 100,
    "ROBOT": 100,
}

# ---------------------------------------------------------------------------
# DEVICE WRAPPER
# ---------------------------------------------------------------------------

def device_wrapper(
    device_type: str,
    func: Callable,
    samples: int,
    interval: float,
    device_id: str,
    results_q: queue.Queue,
    stop_event: threading.Event,
):
    """Runs a single device test and records results."""

    logger.info(colorize(device_type, f"[{device_type}] {device_id} starting..."))
    start = time.perf_counter()

    result = {
        "device_id": device_id,
        "device_type": device_type,
        "samples_requested": samples,
        "samples_sent": 0,
        "errors": 0,
        "duration_s": 0.0,
    }

    try:
        output = func(samples, interval, device_id, stop_event)

        if isinstance(output, dict):
            result["samples_sent"] = output.get("samples_sent", 0)
            result["errors"] = output.get("errors", 0)
        else:
            result["samples_sent"] = samples

    except Exception as e:
        logger.exception(f"[{device_type}] {device_id} ERROR")
        result["errors"] = samples
        result["error"] = str(e)

    finally:
        end = time.perf_counter()
        result["duration_s"] = end - start
        results_q.put(result)

        logger.info(
            colorize(
                device_type,
                f"[{device_type}] {device_id} finished  "
                f"{result['samples_sent']}/{samples} "
                f"errors={result['errors']}  "
                f"{result['duration_s']:.3f}s"
            )
        )


# ---------------------------------------------------------------------------
# RUN A SINGLE TEST CYCLE
# ---------------------------------------------------------------------------

def run_single_test_cycle(device_counts: dict, interval: float, stress_metadata: dict):
    """
    Runs a test cycle using current:
    - device_counts
    - interval
    Returns a list of result dicts.
    """

    logger.info(colorize("MAIN", f"[MAIN] Running cycle IMU={device_counts['IMU']} CAM={device_counts['CAMERA']} ROBOT={device_counts['ROBOT']} INT={interval:.4f}"))

    results_q = queue.Queue()
    stop_event = threading.Event()
    threads = []

    for dev_type, count in device_counts.items():
        func = CLIENT_FUNCTIONS[dev_type]
        samples = DEFAULT_DEVICE_SAMPLES[dev_type]

        for i in range(count):
            device_id = f"{DEVICE_ID_PREFIX[dev_type]}_{i+1}"

            t = threading.Thread(
                target=device_wrapper,
                args=(dev_type, func, samples, interval, device_id, results_q, stop_event),
                daemon=False,
            )
            threads.append(t)
            t.start()

    for t in threads:
        t.join()

    results = []
    while not results_q.empty():
        r = results_q.get()
        r.update(stress_metadata)
        results.append(r)

    return results


# ---------------------------------------------------------------------------
# STRESS TEST
# ---------------------------------------------------------------------------

def run_stress_test(config: dict):
    """
    Executes a real incremental stress test.
    Every step:
        - Increases IMU/CAM/ROBOT device count
        - Decreases interval
    """

    # Current values
    imu = config["start_imu"]
    cam = config["start_cam"]
    robot = config["start_robot"]
    interval = config["start_interval"]

    # Tracking maximum achieved
    max_state = {
        "imu": imu,
        "cam": cam,
        "robot": robot,
        "min_interval": interval,
    }

    all_results = []

    for step in range(1, config["max_steps"] + 1):

        logger.info(colorize("STRESS", f"\n========== STRESS STEP {step} =========="))
        logger.info(colorize("STRESS", f"IMU={imu} CAM={cam} ROBOT={robot} INTERVAL={interval:.4f}"))

        # Prepare arguments
        device_counts = {
            "IMU": imu,
            "CAMERA": cam,
            "ROBOT": robot,
        }

        stress_metadata = {
            "step": step,
            "imu": imu,
            "cam": cam,
            "robot": robot,
            "interval": interval,
        }

        # Run the test
        results = run_single_test_cycle(device_counts, interval, stress_metadata)
        all_results.extend(results)

        # Evaluate success
        total_errors = sum(r["errors"] for r in results)
        if total_errors == 0:
            max_state["imu"] = imu
            max_state["cam"] = cam
            max_state["robot"] = robot
            max_state["min_interval"] = interval

        # Sleep between steps
        time.sleep(config["step_duration_s"])

        # 🎯 INCREMENT COUNTS PROPERLY
        imu = min(imu + config["imu_step"], config["max_imu"])
        cam = min(cam + config["cam_step"], config["max_cam"])
        robot = min(robot + config["robot_step"], config["max_robot"])

        # 🎯 DECREMENT INTERVAL PROPERLY
        interval = max(config["min_interval"], interval + config["interval_step"])

        # Stop if fully saturated
        if (imu == config["max_imu"] and
            cam == config["max_cam"] and
            robot == config["max_robot"] and
            interval == config["min_interval"]):
            logger.info("[STRESS] Reached maximum bound. Ending early.")
            break

    # Save ALL results
    df = pd.DataFrame(all_results)
    os.makedirs("test_results", exist_ok=True)
    outfile = "test_results/stress_results.csv"
    df.to_csv(outfile, index=False)

    logger.info("\n===== FINAL MAXIMUM REACHED =====")
    logger.info(f"IMU Devices:      {max_state['imu']}")
    logger.info(f"Camera Devices:   {max_state['cam']}")
    logger.info(f"Robot Devices:    {max_state['robot']}")
    logger.info(f"Minimum Interval: {max_state['min_interval']:.4f}s")
    logger.info(f"Saved: {outfile}\n")

    return max_state, outfile


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"

    if mode == "stress":
        from stress_config import STRESS_CONFIG
        run_stress_test(STRESS_CONFIG)
    else:
        print("Normal test mode temporarily removed for v3. Use: python3 full_system_tester_v3.py stress")