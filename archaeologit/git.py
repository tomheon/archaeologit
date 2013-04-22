"""
Functions to help run git commands.

All functions take a git_exe keyword argument defaulted to None.  If
it is None, they'll try to consult the env variable
ARCHAEOLOGIT_GIT_EXE for the exe to use.  If the env variable is not
set or is empty, they'll default to use "/usr/bin/env git" which
should work fine on most systems.
"""

from contextlib import contextmanager
import os
from subprocess import call

from archaeologit import log, util

DEFAULT_GIT_EXE = '/usr/bin/env git'

ARCHAEOLOGIT_GIT_EXE_ENV_VAR = 'ARCHAEOLOGIT_GIT_EXE'


class GitExeException(Exception):
    """
    Thrown when the external git exe doesn't return a 0.
    """
    pass


def find_git_root(git_repo_or_subdir):
    """
    Returns a real, absolute path to the git root, assuming that
    `git_repo_or_subdir` is a real, absolute path to either a git repo
    or subdir under it.
    """
    cmd = 'rev-parse --show-toplevel'.split()
    with git_cmd(cmd, cwd=git_repo_or_subdir) as out_f:
        git_root = out_f.read().strip()
    return util.real_abs_path(git_root)


@contextmanager
def git_cmd(cmd, cwd, git_exe=None):
    """
    Run a git cmd and yield an open temporary file to the output.

    After the yield returns, the temporary file is removed.

    The file is returned, rather than a string containing the output,
    because the output of some of the commands we use is large.

    If the git cmd doesn't return 0, raise a GitExeException.

    - `cmd`: a list of strings, as you would pass to subprocess.Popen.

    - `cwd`: the directory to run the command in (as
      subprocess.Popen's cwd param).

    - `git_exe`: the git exe to use to run the command (will be passed
      through resolve_git_exe, see that for rules).
    """
    git_exe = resolve_git_exe(git_exe)
    final_cmd = git_exe.split() + cmd
    # mk_tmpdir will clean up the entire directory recursively for us
    with util.mk_tmpdir() as tmp_dir:
        stdout_fname = os.path.join(tmp_dir, 'stdout')
        stderr_fname = os.path.join(tmp_dir, 'stderr')
        with open(stdout_fname, 'wb') as o_f, open(stderr_fname, 'wb') as e_f:
            returncode = call(final_cmd, stdout=o_f, stderr=e_f, cwd=cwd)
            if returncode != 0:
                git_cmd_s = _fmt_cmd_for_log(final_cmd)
                err_msg = '\n'.join([util.utf8(util.read_file(stderr_fname)),
                                     util.utf8(util.read_file(stdout_fname))])
                log.error("Error running %s: %s" % (util.utf8(git_cmd_s),
                                                    err_msg))
                raise GitExeException(
                    "Git command %s returned %d with err log %s" %
                    (git_cmd_s,
                     returncode,
                     err_msg))
            else:
                # re-open the stdout file so we don't get any wonky fp
                # stuff
                with open(stdout_fname, 'rb') as stdout_fil:
                    yield stdout_fil


def resolve_git_exe(git_exe):
    """
    If git_exe is non-None, return it.

    Otherwise, if the environment variable ARCHAEOLOGIT_GIT_EXE is set
    and non-empty, return it.

    Otherwise, return DEFAULT_GIT_EXE.
    """
    if git_exe:
        return git_exe
    else:
        env_git_exe = os.environ.get(ARCHAEOLOGIT_GIT_EXE_ENV_VAR)
        if env_git_exe:
            return env_git_exe
        else:
            return DEFAULT_GIT_EXE


def _fmt_cmd_for_log(cmd):
    """
    Join the git_cmd, quoting individual segments first so that
    it's relatively easy to see if there were whitespace issues or
    not.
    """
    return ' '.join(['"%s"' % util.utf8(seg) for seg in cmd])
