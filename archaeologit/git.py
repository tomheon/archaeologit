"""
Functions to help run git commands.

All functions take a git_exe keyword argument defaulted to None.  If
it is None, they'll try to consult the env variable
ARCHAEOLOGIT_GIT_EXE for the exe to use.  If the env variable is not
set or is empty, they'll default to use "/usr/bin/env git" which
should work fine on most systems.
"""

import os
from subprocess import Popen, PIPE

from archaeologit import log, util

DEFAULT_GIT_EXE = '/usr/bin/env git'

ARCHAEOLOGIT_GIT_EXE_ENV_VAR = 'ARCHAEOLOGIT_GIT_EXE'


class GitExeException(Exception):
    """
    Thrown when the external git exe doesn't return a 0.
    """
    pass


def git_cmd(cmd, cwd, git_exe=None):
    """
    Run a git cmd and return what it printed to stdout.

    If the git cmd doesn't return 0, raise a GitExeException.

    - `cmd`: a list of strings, as you would pass to subprocess.Popen.

    - `cwd`: the directory to run the command in (as
      subprocess.Popen's cwd param).

    - `git_exe`: the git exe to use to run the command (will be passed
      through resolve_git_exe, see that for rules).
    """
    git_exe = resolve_git_exe(git_exe)
    final_cmd = git_exe.split() + cmd
    git_p = Popen(final_cmd, stdout=PIPE, stderr=PIPE, cwd=cwd)
    (out, err) = git_p.communicate()
    if git_p.returncode != 0:
        git_cmd_s = _fmt_cmd_for_log(final_cmd)
        log.error("Error running %s: %s" % (util.utf8(git_cmd_s), err))
        raise GitExeException("Git command %s returned %d" %
                              (git_cmd_s,
                               git_p.returncode))
    return out


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
    return ' '.join(['"%s"' % seg for seg in cmd])
