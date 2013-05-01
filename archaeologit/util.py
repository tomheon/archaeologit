"""
Random utilities, largely file and string based, that didn't really
fit in other places.
"""

from contextlib import contextmanager
import errno
import os
import re
import shutil
import tempfile


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


@contextmanager
def mk_tmpdir():
    """
    Make a temp dir and yield it, removing it afterwards.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)


def read_file(fname):
    """
    Open and read fname, returning its whole contents.

    Then close the file.
    """
    with open(fname, 'rb') as fil:
        return fil.read()


# By default, read one meg at a time.
DEFAULT_READ_FILE_CHUNKED_READ_SIZE = 1024 * 1024


def split_file(fil, sep_char='\0',
               read_size=DEFAULT_READ_FILE_CHUNKED_READ_SIZE):
    """
    Split the contents of a file `fil` along the lines of
    string.split(), with two important differences:

    - the splits are yielded in generator form, rather than returned
      as a list

    - `sep_char` can only be a single character string, or a
      ValueError will be raised

    The `read_size` argument determines how much of the file should be
    read in each gulp.  Note that this does *not* put a hard bound on
    memory usage, as each split is read fully into memory, and one
    split may be larger than `read_size`.
    """
    if len(sep_char) != 1:
        raise ValueError("Can only split file on single char")

    esc_sep = re.escape(sep_char)
    compiled_sep = re.compile(esc_sep)

    # seed the buffer with an empty string so that calling split_file
    # on an empty file will yield an empty string, like ''.split().
    # The empty string won't affect any other cases.
    buf = ['']
    while True:
        chunk = fil.read(read_size)
        if not chunk:
            break

        check_positions = [m.start() for m in compiled_sep.finditer(chunk)]
        last_pos = len(chunk) - 1

        # to make it easier on ourselves, make sure that the last
        # position of the chunk is a position we'll check
        if not check_positions or check_positions[-1] != last_pos:
            check_positions.append(last_pos)

        cur_pos = 0
        for check_pos in check_positions:
            to_append = chunk[cur_pos:check_pos + 1]
            if to_append.endswith(sep_char):
                to_append = to_append[:-1]
                buf.append(to_append)
                yield ''.join(buf)
                # to handle the case in which the file ends with a
                # sep, we want to preserve string.split()-like
                # behaviour and keep an empty string.  In other cases,
                # when more data follows, the empty string won't do
                # anything.
                buf = ['']
            else:
                buf.append(to_append)
            cur_pos = check_pos + 1

    if buf:
        yield ''.join(buf)


@contextmanager
def temp_fname():
    """
    Yield a temp file name, delete the file afterwards.
    """
    ntf = tempfile.NamedTemporaryFile(delete=False)
    fname = ntf.name
    ntf.close()
    try:
        yield fname
    finally:
        try:
            os.unlink(fname)
        except OSError:
            # this means it was already unlinked
            pass


def rel_fname(dirname, fname):
    """
    Assuming `fname` is at some level under `dirname`, and that both
    are real absolute paths, return `fname` as relative to `dirname`.

    >>> rel_fname("/tmp/something/one", "/tmp/something/one/two/three.txt")
    'two/three.txt'

    >>> rel_fname("/tmp/something/one/", "/tmp/something/one/two/three.txt")
    'two/three.txt'
    """
    if not fname.startswith(dirname):
        raise ValueError("Can't take relative path for non-relative file"
                         "%s %s" % (dirname, fname))
    dirname_len = len(dirname)
    if not dirname.endswith('/'):
        dirname_len += 1
    return fname[dirname_len:]


def ensure_containing_dir_exists(fname):
    """
    Ensure that the containing directory for `fname` exists.

    E.g. if fname is "/tmp/something/one/two.txt", recursively create
    "/tmp", "/tmp/something", and "/tmp/something/one" if needed.
    """
    mkdir_p(os.path.dirname(fname))
