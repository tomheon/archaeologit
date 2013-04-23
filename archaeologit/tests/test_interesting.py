import re

from nose.tools import eq_

from archaeologit.interesting import is_interesting_fname


TEST_INTERESTING_FNAMES_DATA = [
    ([], [], "", True),
    ([], [], "hello", True),
    ([], [], "hello.txt", True),

    ([r".*\.txt"], [], "/test/this.txt", True),
    ([r".*\.txt", r".*"], [], "/test/this.txt", True),
    ([r".*\.txt", r".*\.doc"], [], "/test/this.txt", True),
    ([r".*\.doc"], [], "/test/this.txt", False),

    ([], [r".*\.txt"], "/test/this.txt", False),
    ([], [r".*\.txt", r".*"], "/test/this.txt", False),
    ([], [r".*\.txt", r".*\.doc"], "/test/this.txt", False),
    ([], [r".*\.doc"], "/test/this.txt", True),

    ([r".*\.txt"], [r".*\.doc"], "this.txt", True),
    ([r".*\.txt"], [r".*\.txt"], "this.txt", True),
    ([r".*\.xls"], [r".*\.doc"], "this.txt", True),
    ([r".*\.xls"], [r".*\.txt"], "this.txt", False),
]


def test_interesting_fnames():
    for (interesting_res,
         boring_res,
         fname,
         expected) in TEST_INTERESTING_FNAMES_DATA:
        yield (_check_interesting_fname, interesting_res,
               boring_res, fname, expected)


def _check_interesting_fname(interesting_res, boring_res,
                             fname, expected):
    eq_(expected, is_interesting_fname(fname,
                                       [re.compile(r)
                                        for r
                                        in interesting_res],
                                       [re.compile(r)
                                        for r
                                        in boring_res]))
