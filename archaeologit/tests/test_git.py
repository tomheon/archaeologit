import os

from nose.tools import eq_, ok_, raises
from impermagit import fleeting_repo

from archaeologit.git import DEFAULT_GIT_EXE, resolve_git_exe, \
    ARCHAEOLOGIT_GIT_EXE_ENV_VAR, git_cmd, find_git_root
from archaeologit.tutil import env_setting, REMOVE_FROM_ENV
from archaeologit import util


def test_find_git_root():
    with fleeting_repo() as test_repo:
        test_repo.commit([('test_proj/test.txt', 'testing\n')])
        git_root = test_repo.repo_root
        test_proj_root = os.path.join(git_root, 'test_proj')
        # should work both for subdirectories
        eq_(git_root, find_git_root(test_proj_root))
        # and for top-level projects
        eq_(git_root, find_git_root(git_root))


@raises(util.WrappedPopenException)
def test_find_git_root_barfs_on_non_repo():
    with util.mk_tmpdir() as temp_dir:
        find_git_root(temp_dir)


def test_resolve_git_exe_defaults():
    with env_setting(ARCHAEOLOGIT_GIT_EXE_ENV_VAR, REMOVE_FROM_ENV):
        eq_(DEFAULT_GIT_EXE, resolve_git_exe(None))


def test_resolve_git_exe_consults_env():
    fake_git = 'fakegit'
    with env_setting(ARCHAEOLOGIT_GIT_EXE_ENV_VAR, fake_git):
        eq_(fake_git, resolve_git_exe(None))


def test_resolve_git_exe_arg_trumps_all():
    fake_git_one = 'fakegit_one'
    fake_git_two = 'fakegit_two'
    ok_(fake_git_one != fake_git_two)
    with env_setting(ARCHAEOLOGIT_GIT_EXE_ENV_VAR, fake_git_one):
        eq_(fake_git_two, resolve_git_exe(fake_git_two))


def test_can_call_git():
    # just to make sure we've got a git exe and can test that bad args
    # are actually causing the exception in other tests of exceptions
    with git_cmd(["--version"], cwd='.') as out_f:
        ok_(out_f.read())


@raises(util.WrappedPopenException)
def test_git_cmd_barfs_on_bad_cmd():
    with git_cmd(["not_a_git_cmd"], cwd='.'):
        # should never get here
        ok_(False)


def test_git_cmd_returns_std_out():
    with fleeting_repo() as test_repo:
        commit_msg = 'I remain committed.'
        test_repo.commit([('test.txt', 'testing\n')],
                         commit_msg=commit_msg)

        with git_cmd(["log"], cwd=test_repo.repo_root) as output_f:
            ok_(commit_msg in util.utf8(output_f.read()))
