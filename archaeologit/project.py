from collections import namedtuple
import re

from archaeologit import log, util, git


# author, log_msg, and diff are all unicodes.
#
# All of them are decoded using errors=replace.
#
LogEntry = namedtuple('LogEntry',
                      'author log_msg diff')


class Project(object):
    """
    Represents a single project directory.
    """

    def __init__(self, project_root):
        """
        - `project_root`: the real path to the root of the project
        (note that this may differ from the root of the git repo, if
        you're housing several projects in the same repo)
        """
        self.project_root = util.real_abs_path(project_root)
        self.git_root = self._find_git_root()

    def ls(self):
        """
        List the entire tree that git is aware of in the project root.

        Returns the file names as real, absolute paths.
        """
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
        git_cmd.append(self.project_root)

        fnames_z = self._git_cmd(git_cmd)

        return [util.real_abs_path(fname=fname, parent=self.git_root)
                for fname
                in fnames_z.split('\0')
                # don't show '', which is just the root of the repo.
                if fname]

    def parsed_log(self, fname):
        """
        Return parsed logs as a list of LogEntry named tuples.
        """
        return self._parse_log(fname)

    def _find_git_root(self):
        git_cmd = 'rev-parse --show-toplevel'.split()
        # we have to pass project_root as the cwd for the command, as
        # we don't yet know the git_root (we're in the process of
        # trying to figure that out here) but we do know it's at or
        # above the project root.
        git_root = self._git_cmd(git_cmd, cwd=self.project_root).strip()
        return util.real_abs_path(git_root)

    def _git_cmd(self, git_cmd, cwd=None):
        """
        Run a git cmd and return what it printed to stdout.

        If cwd is None, run the git command in the git root,
        otherwise, run it in cwd.
        """
        if cwd is None:
            cwd = self.git_root
        return git.git_cmd(git_cmd, cwd=cwd)

    def _parse_log(self, fname):
        parsed_entries = []
        # -z = null byte separate log entries
        #
        # -w = ignore all whitespace when calculating changed lines
        #
        # --follow = follow file history through renames
        #
        # --patience = use the patience diff algorithm
        #
        # --encoding=utf-8 forces any logs that were not encoded as
        #   utf-8 to be re-encoded as utf-8 before they are returned
        #
        # -p show patches (diffs)
        #
        git_cmd = ("log -z -w --follow --patience "
                   "-p --encoding=utf-8 -- ").split()
        # don't append the fname until after the split, as it might
        # contain spaces.
        git_cmd.append(fname)
        out = self._git_cmd(git_cmd)

        # A note on the encodings.  Git doesn't give us a way to get
        # at the encodings of the files / diffs (short of
        # .gitattributes, which has to be set by the original
        # producers of the repo).  We assume that the encoding is
        # UTF-8, and just replace everything else with that lovely
        # question mark thing.
        log_entries = [entry.decode('utf-8', errors='replace')
                       for entry
                       in out.split('\0')
                       if entry.strip()]
        parsed_entries = [self._parse_entry(entry)
                          for entry
                          in log_entries]
        parsed_entries = filter(None, parsed_entries)
        # put the oldest entries first (git log shows the newest
        # first)
        parsed_entries.reverse()
        return parsed_entries

    def _parse_entry(self, entry):
        """
        Parse a single git log entry into a LogEntry, or return None
        if it can't be parsed.
        """
        split_entry = self._split_entry_header(entry)
        if split_entry is None:
            return None
        header_lines, diff_lines = split_entry

        diff = '\n'.join(diff_lines)
        if not diff.strip():
            log.info("Diff appeared to be empty, skipping.")
            return None
        author = self._parse_author(header_lines)
        if not author:
            log.info("Could not parse author, skipping.")
            return None
        log_msg = '\n'.join(self._parse_log_msg(header_lines))
        return LogEntry(author=util.uc(author),
                        log_msg=util.uc(log_msg),
                        diff=util.uc(diff))

    def _parse_log_msg(self, header_lines):
        """
        The log message begins with the first line that begins with a
        space or is empty, and continues until the first line
        beginning with anything else.

        Returns the log message lines as a list.
        """
        log_msg_lines = []
        for line in header_lines:
            if line.startswith((u' ', u'\t')) or not line.strip():
                log_msg_lines.append(line)
            elif log_msg_lines:
                break
        return log_msg_lines

    def _parse_author(self, header_lines):
        """
        Parse the author name out of the the list of header lines.

        Assume that the author line is there, waiting to be parsed,
        since otherwise the _split_entry_header step would have
        refused to continue.
        """
        # preserve any spaces that showed up in the name (though
        # collapsed)
        segs = re.split(r'\s+', header_lines[1].strip())
        return ' '.join(segs[1:-1])

    def _split_entry_header(self, entry):
        """
        Parse `entry`, which is a single git log entry, diff and all,
        into a (header_lines, diff_lines) tuple, where header is
        everything before the line beginning with 'diff', and diff is
        everything after, including that line.

        So header typically includes the commit hash, the date, the
        author, and the log msg.

        If there's no diff, no commit hash, or no author, this logs
        the fact and returns None (these can happen in a number of
        normal circumstances, including e.g. binary files, which we
        don't want anyway).
        """
        lines = entry.split('\n')
        # just in case of \r\n fun
        lines = [line.rstrip('\r') for line in lines]
        if not lines or len(lines) < 2:
            log.info("Empty entry, skipping.")
            return None
        if not lines[0].startswith("commit"):
            log.info("No commit line, skipping.")
            return None
        if not lines[1].startswith("Author"):
            log.info("No author line, skipping.")
            return None
        # Start after the author line and look for the diff line.
        ind = 2
        lines_len = len(lines)
        while ind < lines_len and not lines[ind].startswith('diff'):
            ind += 1

        # call everything before the diff line the header, the rest
        # the diff.
        return lines[:ind], lines[ind:]
