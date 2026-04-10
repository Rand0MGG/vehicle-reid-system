import logging


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level_name: str = "INFO") -> None:
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(level=level, format=LOG_FORMAT)

    root_logger.setLevel(level)
