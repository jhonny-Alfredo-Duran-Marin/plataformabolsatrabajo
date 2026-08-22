import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configura el logging estándar de la aplicación."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
