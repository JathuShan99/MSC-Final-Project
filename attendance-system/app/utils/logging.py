import logging
from app.config.paths import LOG_DIR

def setup_logger():
    logger = logging.getLogger("AttendanceSystem")
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOG_DIR / "system.log")
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


