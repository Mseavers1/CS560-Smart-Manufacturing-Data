# stress_config.py
"""
Configuration file for the v3 stress tester.
These values are consumed by full_system_tester_v3.py

Tune these based on desired load scaling.
"""

STRESS_CONFIG = {

    # -------------------------------------------------
    # STARTING LOAD
    # -------------------------------------------------
    "start_imu": 1,
    "start_cam": 1,
    "start_robot": 1,

    # Starting interval between samples (seconds)
    # Example: 0.01 = 10ms between samples
    "start_interval": 0.03,


    # -------------------------------------------------
    # MAXIMUM LOAD LIMITS
    # The stress test will never exceed these.
    # -------------------------------------------------
    "max_imu": 50,
    "max_cam": 10,
    "max_robot": 1,

    # Minimum allowed interval (cannot go faster than this)
    "min_interval": 0.005,   # 5ms


    # -------------------------------------------------
    # PER-STEP INCREMENTS
    # Actual stress scaling happens here.
    # -------------------------------------------------

    # Increase device counts each step
    "imu_step": 1,
    "cam_step": 1,
    "robot_step": 0,

    # Decrease interval each step (negative means faster)
    # Example: -0.001 = subtract 1ms from interval each step
    "interval_step": -0.001,


    # -------------------------------------------------
    # EXECUTION CONTROL
    # -------------------------------------------------

    # Duration to wait between steps (seconds)
    "step_duration_s": 1.0,

    # Hard cap on test duration in steps
    "max_steps": 200,
}