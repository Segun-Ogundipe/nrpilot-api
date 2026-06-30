import logging
import sys
from os import environ
from typing import Any, TextIO

import structlog
from pythonjsonlogger import json


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structured logging with JSON output.

    Sets up both structlog and the Python logging module to work together,
    providing structured logging with context preservation.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    is_dev: bool = environ.get("ENV", "development").lower() in ("dev", "development")

    handlers: list[logging.Handler] = []

    console_handler: logging.StreamHandler[TextIO | Any] = logging.StreamHandler(
        sys.stdout
    )
    if is_dev:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = json.JsonFormatter(
            "%(timestamp)s %(name)s %(levelname)s %(message)s", timestamp=True
        )
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.dev.ConsoleRenderer()
                if is_dev
                else structlog.processors.JSONRenderer()
            ),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
