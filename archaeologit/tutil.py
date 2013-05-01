"""
Utilities for testing archaeologit.

Many depend on having access to a git exe.  They default to using
/usr/bin/env git, which should work on most platforms, but if you need
to override that, you can set an environment variable for:

ARCHAEOLOGIT_GIT_EXE

to the right exe.
"""

from contextlib import contextmanager
import os

from nose.tools import nottest


# flag used in env_setting to indicate that an env variable is to be
# removed
REMOVE_FROM_ENV = object()


@contextmanager
def env_setting(key, value):
    """
    Yield with an ENV setting of key => value, replace it afterwards.
    """
    had_key = key in os.environ
    orig_val = os.environ.get(key)
    try:
        if value is REMOVE_FROM_ENV:
            if key in os.environ:
                del os.environ[key]
        else:
            os.environ[key] = value
        yield
    finally:
        if not had_key:
            if key in os.environ:
                del os.environ[key]
        else:
            os.environ[key] = orig_val


@nottest
def read_test_fname(fname):
    """
    Assuming that fname is under "tests/testfiles", read and return
    the contents.
    """
    with open(os.path.join(os.path.dirname(__file__),
                           'tests',
                           'testfiles',
                           fname),
              'rb') as fil:
        return fil.read()
