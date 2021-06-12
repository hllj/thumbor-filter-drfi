import logging

__version__ = "0.0.1"

try:
    from drfi.removebg import Filter
except ImportError:
    logging.exception("Could not import thumbor filter")
