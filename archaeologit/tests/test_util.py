from StringIO import StringIO

from nose.tools import eq_, raises

from archaeologit.util import split_file, rel_fname


TEST_SPLIT_FILE_DATA = [("null\0byte", "\0"),
                        ("space splits", " "),
                        ("no splits", "\0"),
                        ("ends\0sep\0", "\0"),
                        ("", "\0"),
                        ("\0start\0end\0sep\0", "\0"),
                        ("\0", "\0"),
                        ("re.like.splits", "."),
                        ]


def _check_split_file(data, sep, read_size):
    stringio = StringIO(data)
    eq_(data.split(sep),
        list(split_file(stringio, sep_char=sep, read_size=read_size)))


def test_split_file():
    for data, sep in TEST_SPLIT_FILE_DATA:
        # any read size should produce the same results
        for read_size in range(1, len(data) + 2):
            yield _check_split_file, data, sep, read_size


@raises(ValueError)
def test_split_file_barfs_on_multi_char_sep():
    stringio = StringIO("hi there")
    # call list to invoke the generator
    list(split_file(stringio, sep_char="th"))


@raises(ValueError)
def test_split_file_barfs_on_empty_sep():
    stringio = StringIO("hi there")
    # call list to invoke the generator
    list(split_file(stringio, sep_char=""))


REL_FNAME_TEST_DATA = [("", "", ""),
                       ("/home/test/this",
                        "/home/test/this",
                        ""),
                       ("/home/test/",
                        "/home/test/this/thing.txt",
                        "this/thing.txt"),
                       ("/home/test/",
                        "/home/test/thing.txt",
                        "thing.txt")]


def test_rel_fname_finds_relative_fname():
    for (dirname, fname, expected_rel_fname) in REL_FNAME_TEST_DATA:
        yield _check_rel_fname, dirname, fname, expected_rel_fname


def _check_rel_fname(dirname, fname, expected_rel_fname):
    eq_(expected_rel_fname, rel_fname(dirname, fname))


@raises(ValueError)
def test_rel_fname_barfs_on_non_rel_file():
    rel_fname("/test/this", "/something/else.txt")
