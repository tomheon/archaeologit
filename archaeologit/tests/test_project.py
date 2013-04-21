import os

from nose.tools import ok_, eq_

from archaeologit.project import Project
from archaeologit.tutil import mk_test_repo
from archaeologit import util


def _get_single_entry(body="test.\n", commit_msg=None, author=None):
    with mk_test_repo() as test_repo:
        test_repo.commit([('test.txt', util.utf8(body))],
                         commit_msg=commit_msg,
                         author=author)
        proj = Project(test_repo.repo_root)
        expected_test_fname = os.path.join(test_repo.repo_root,
                                           'test.txt')
        logs_for_test_txt = proj.parsed_log(expected_test_fname)
        eq_(1, len(logs_for_test_txt))
        return logs_for_test_txt[0]


def test_unicode_in_source_does_not_barf():
    unicode_line = u"this is \u2603 a test\n"
    log_entry = _get_single_entry(body=unicode_line)
    ok_(unicode_line in log_entry.diff)


def test_unicode_in_log_does_not_barf():
    unicode_line = u"this is \u2603 a test\n"
    log_entry = _get_single_entry(commit_msg=unicode_line)
    ok_(unicode_line in log_entry.log_msg)


def test_unicode_in_author_does_not_barf():
    unicode_author = u"Frosty the \u2603"
    unicode_author_email = u"%s <frosty@example.com>" % unicode_author
    log_entry = _get_single_entry(author=unicode_author_email)
    ok_(unicode_author in log_entry.author)
