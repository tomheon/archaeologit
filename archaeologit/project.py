from archaeologit import util, git


def ls(project_root):
    """
    Return a list of real, absolute paths to all the git-controlled
    files under the project root.
    """
    git_root = git.find_git_root(project_root)

    # --full-tree = allow absolute path for final argument (pathname)
    #
    # --name-only = don't show the git id for the object, just the
    #   file name
    #
    # -r = recurse into subdirs
    #
    # -z = null byte separate listings
    git_cmd_s = 'ls-tree --full-tree --name-only -r -z HEAD'
    # don't add the project root until after the split, in case it
    # contains spaces.
    git_cmd = git_cmd_s.split()
    git_cmd.append(project_root)
    with git.git_cmd(cmd=git_cmd, cwd=git_root) as out_f:
        fnames_z = out_f.read()
        return [util.real_abs_path(fname=fname, parent=git_root)
                for fname
                in fnames_z.split('\0')
                # don't show '', which is just the root of the repo.
                if fname]
