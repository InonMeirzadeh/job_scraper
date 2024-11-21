import logging


def configure_logging(log_level=logging.INFO, log_format='%(asctime)s - %(levelname)s - %(message)s'):
    """
    Configures the logging system with the given level and format.
    """
    logging.basicConfig(level=log_level, format=log_format)
    logging.info("Logging configuration initialized.")
