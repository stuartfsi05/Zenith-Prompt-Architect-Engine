import logging
from pathlib import Path

from rich.logging import RichHandler


def setup_logger(name: str = "Zenith", log_level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a centralized logger with RichHandler for console
    and FileHandler for file logging.

    Args:
        name (str): The name of the logger. Defaults to "Zenith".
        log_level (int): The logging level. Defaults to logging.INFO.

    Returns:
        logging.Logger: Configured logger instance.
    """

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "zenith.log"

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console Handler (Rich)
    console_handler = RichHandler(
        rich_tracebacks=True, markup=True, show_time=True, show_path=False
    )
    console_handler.setLevel(log_level)
    console_format = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_format)

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_format)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
