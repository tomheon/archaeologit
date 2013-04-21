"""
Random utilities that didn't really fit in other places.
"""

import errno
import os


def real_abs_path(fname, parent=None):
    """
    Return the real (meaning symlinks have been dereferenced) absolute
    (meaning rooted at / and containing no ../ or the like) path of
    fname.

    If parent is None, it's ignored.  Otherwise, fname is assumed to
    relative to parent.
    """
    if parent is not None:
        fname = os.path.join(parent, fname)

    return os.path.realpath(os.path.abspath(fname))


def mkdir_p(path):
    """
    Emulate mkdir -p functionality.

    Adaped from:

    http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
    """
    try:
        os.makedirs(path)
    except OSError, exc:
        if exc.errno != errno.EEXIST or not os.path.isdir(path):
            raise


def uc(uc_or_str_in_unknown_enc):
    """
    Return a unicode version of str_in_unknown_enc, currently assumed
    to be utf-8.  Errors in decoding use python's 'replace'.
    """
    if isinstance(uc_or_str_in_unknown_enc, unicode):
        return uc_or_str_in_unknown_enc
    else:
        return uc_or_str_in_unknown_enc.decode('utf-8', errors='replace')


def utf8(uc_or_str_in_unknown_enc):
    """
    Return a utf-8 encoded string of uc_or_str_in_unknown_enc,
    potentially with replace chars on errors.
    """
    return uc(uc_or_str_in_unknown_enc).encode('utf-8',
                                               errors='replace')
