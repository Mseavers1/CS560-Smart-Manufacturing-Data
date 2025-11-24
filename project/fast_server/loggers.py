import logging
from datetime import datetime, timezone
from pathlib import Path

cur_camera_logger: logging.Logger | None = None
cur_imu_logger: logging.Logger | None = None
cur_robot_logger: logging.Logger | None = None
system_logger: logging.Logger | None = None
system_logger_date = None

formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def create_logger(logger, name):
    
    LOG_DIR = Path("/fast_server/logs")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    logger = logging.getLogger(f"{name}_{timestamp}_utc")

    if not logger.handlers:
        handler = logging.FileHandler(LOG_DIR / f"{name}_{timestamp}.log")
        handler.setFormatter(formatter)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False
    
    return logger


def create_system_logger() -> None:
    global system_logger, system_logger_date

    utc_date = datetime.now(timezone.utc).strftime("%Y%m%d")

    # Recreate logger if date changes
    if system_logger is None or system_logger_date != utc_date:
        system_logger_date = utc_date
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        system_logger = create_logger("system_logger", timestamp)

        system_logger.info(f"Created new system logger for {utc_date}")


def log_system_logger(msg: str, isError: bool = False) -> None:
    create_system_logger()

    if isError:
        system_logger.error(msg)
    else:
        system_logger.info(msg)



def create_loggers() -> None:
    global cur_camera_logger, cur_imu_logger, cur_robot_logger

    cur_camera_logger = create_logger(cur_camera_logger, "camera_logger")
    cur_imu_logger = create_logger(cur_imu_logger, "imu_logger")
    cur_robot_logger = create_logger(cur_robot_logger, "robot_logger")
