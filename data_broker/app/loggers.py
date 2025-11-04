# loggers.py
from datetime import datetime
import logging
from pathlib import Path

cur_camera_logger: logging.Logger | None = None
cur_imu_logger: logging.Logger | None = None
cur_robot_logger: logging.Logger | None = None

def create_loggers() -> None:
    """Create (or reuse) file-backed loggers."""
    global cur_camera_logger, cur_imu_logger, cur_robot_logger  # <<< important

    LOG_DIR = Path("/app/logs")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create/get named loggers
    cur_camera_logger = logging.getLogger(f"camera_logger_{timestamp}")
    cur_imu_logger    = logging.getLogger(f"imu_logger_{timestamp}")
    cur_robot_logger  = logging.getLogger(f"robot_logger_{timestamp}")

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] (%(name)s): %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    # Attach handlers once per new logger
    for logger, name in [
        (cur_camera_logger, "camera"),
        (cur_imu_logger, "imu"),
        (cur_robot_logger, "robot"),
    ]:
        if not logger.handlers:
            handler = logging.FileHandler(LOG_DIR / f"{name}_{timestamp}.log")
            handler.setFormatter(formatter)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.propagate = False  # keep logs out of root logger
