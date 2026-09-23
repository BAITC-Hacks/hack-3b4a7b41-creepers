import logging


def configure_logging() -> None:
    # Do not log HTTP requests, auth headers, upstream bodies or chat messages.
    for name in ("httpx", "httpcore"):
        logger = logging.getLogger(name)
        logger.setLevel(logging.CRITICAL)
        logger.propagate = False
