import logging


def configure_logging() -> None:
    # Cart URLs contain bearer session IDs; do not include them in access logs.
    logging.getLogger("uvicorn.access").disabled = True
    # Do not log HTTP requests, auth headers, upstream bodies or chat messages.
    for name in ("httpx", "httpcore"):
        logger = logging.getLogger(name)
        logger.setLevel(logging.CRITICAL)
        logger.propagate = False
