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
import shutil
import tempfile

from nose.tools import nottest

from archaeologit import git, util


@nottest
class TestRepo(object):
    """
    Provides functions to help create and modify a test git repo to
    make testing of various archaeologit pieces easier.
    """
    def __init__(self, repo_root):
        self.repo_root = repo_root
        self._git_cmd(["init"])

    def commit(self, fnames_with_contents, commit_msg=None, author=None):
        """
        Apply the changes described in fnames_with_contents in the
        repo directory, and then commit the results.

        fnames_with_contents is a list of tuples of the form:

        [(str(fname), str(contents)|None), ...]

        If the contents is not None, the string will be written the
        file indicated by fname.  If contents is None, the file will
        be git rm'ed.

        fname should be relative to the git repo root.  If fname
        contains directory paths, they will be created.

        If commit_msg is None, the commit message will be "Test
        commit."

        If author is None, the author will be:

        "Test Author <test@example.com>".
        """
        for (fname, contents) in fnames_with_contents:
            fpath = os.path.join(self.repo_root, fname)
            self._ensure_dir_for_fname(fpath)
            if contents is None:
                self._git_cmd(["rm", fname])
            else:
                with open(fpath, 'wb') as fil:
                    fil.write(contents)
                self._git_cmd(["add", fname])

        cmd = ["commit", "-m"]
        if commit_msg is None:
            commit_msg = "Test commit."
        cmd.append(commit_msg)
        if author is None:
            author = "Test Author <test@example.com>"
        cmd.append("--author")
        cmd.append(author)
        self._git_cmd(cmd)

    def _git_cmd(self, cmd):
        git.git_cmd(cmd, cwd=self.repo_root)

    def _ensure_dir_for_fname(self, fname):
        util.mkdir_p(os.path.dirname(fname))


@nottest
@contextmanager
def mk_test_repo():
    """
    Create a temp directory and yield a TestRepo built from it.

    After the yield returns, remove the temp dir.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        yield TestRepo(temp_dir)
    finally:
        shutil.rmtree(temp_dir)
