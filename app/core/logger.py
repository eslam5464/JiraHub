import re
import sys

from loguru import logger

SENSITIVE_PATTERNS = re.compile(
    r"(password|token|secret|api_key|encryption_key|authorization)",
    re.IGNORECASE,
)


def sanitize_value(key: str, value: object) -> object:
    """Redact sensitive values in log output."""
    if isinstance(key, str) and SENSITIVE_PATTERNS.search(key):
        return "***REDACTED***"
    if isinstance(value, dict):
        return {k: sanitize_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_value("", item) for item in value]
    return value


def sanitize_dict(data: dict) -> dict:
    """Recursively sanitize a dictionary for logging."""
    return {k: sanitize_value(k, v) for k, v in data.items()}


def setup_logger(debug: bool = False) -> None:
    """Configure loguru logger with console and file outputs."""
    logger.remove()

    log_level = "DEBUG" if debug else "INFO"

    # Console output - colored
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # File output - structured, rotated
    logger.add(
        "logs/app.log",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        enqueue=True,  # Thread-safe
    )
