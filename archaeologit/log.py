"""
Utilities for logging.
"""

import logging
import sys

FORMAT = "%(asctime)s %(message)s"

# by default, log to stderr, as we get better results with
# multiprocessing.
logging.basicConfig(format=FORMAT,
                    stream=sys.stderr)


def debug(*args, **kwargs):
    logging.debug(*args, **kwargs)


def info(*args, **kwargs):
    logging.info(*args, **kwargs)


def warn(*args, **kwargs):
    logging.warn(*args, **kwargs)


def error(*args, **kwargs):
    logging.error(*args, **kwargs)
