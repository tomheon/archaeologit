"""
Utilities for logging.
"""

import logging
import multiprocessing

FORMAT = "%(asctime)s %(message)s"

# by default, log to stderr, as we get better results with
# multiprocessing.

logger = multiprocessing.log_to_stderr()
logger.setLevel(logging.INFO)


def debug(*args, **kwargs):
    logger.debug(*args, **kwargs)


def info(*args, **kwargs):
    logger.info(*args, **kwargs)


def warn(*args, **kwargs):
    logger.warn(*args, **kwargs)


def error(*args, **kwargs):
    logger.error(*args, **kwargs)
