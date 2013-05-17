import os

from impermagit import fleeting_repo
from nose.tools import eq_, raises

from archaeologit import project
from archaeologit import util


def test_ls():
    with fleeting_repo() as test_repo:
        test_repo.commit([('test_proj/test.txt', 'testing\n'),
                          ('test_proj/test2.txt', 'testing\n'),
                          ('test3.txt', 'testing\n')])
        git_root = test_repo.repo_root
        test_proj_root = os.path.join(git_root, 'test_proj')
        # ls on the sub-dir project should not include test3.
        eq_(sorted([os.path.join(test_proj_root, f)
                    for f
                    in ('test.txt', 'test2.txt')]),
            project.ls(test_proj_root))
        # ls on the sub-dir project should include test3.
        eq_(sorted([os.path.join(test_proj_root, f)
                    for f
                    in ('test.txt', 'test2.txt')] +
                   [os.path.join(git_root, 'test3.txt')]),
            project.ls(git_root))


@raises(util.WrappedPopenException)
def test_ls_barfs_on_non_git_repo():
    with util.mk_tmpdir() as temp_dir:
        project.ls(temp_dir)
