"""
Module to read / parse git logs.
"""

from collections import namedtuple
from contextlib import contextmanager
import os
import re

from archaeologit import git, util, log


# Named tuple representing a single git log entry, including diffs.
#
# raw_log is a str() with the raw log, all other fields are unicodes
# decoded with errors='replace', so they should be non-controversial
# in downstream processing.
#
LogEntry = namedtuple('LogEntry',
                      'commit author_name author_email log_msg diff raw_log')


NAME_AND_EMAIL_RE = re.compile("^([^<]+) <(.*)>$")


def parse_name_and_email(author):
    """
    Given an author in git format (e.g. "Bob Jones <bob@example.com>")
    parse the name and email out and return them as (str(name),
    str(email)).  Return None if they can't be parsed.
    """
    match = NAME_AND_EMAIL_RE.match(author)
    if not match:
        return None
    else:
        return (match.group(1), match.group(2))


@contextmanager
def raw_log_stream(fname):
    """
    Yield an open file-like containing the NULL byte delimited raw log
    entries for fname, which will be closed upon return.
    """
    git_root = git.find_git_root(os.path.dirname(fname))
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
    # --reverse show the commits in chronological order
    #
    cmd = ("log -z -w --follow --patience --reverse -p "
           "--encoding=utf-8 -- ").split()
    # don't append the fname until after the split, as it might
    # contain spaces.
    cmd.append(fname)
    with git.git_cmd(cmd, cwd=git_root) as raw_log_entries_z:
        yield raw_log_entries_z


def parse_raw_log(fname):
    with raw_log_stream(fname) as stream:
        for entry in parse_raw_log_stream(stream):
            yield entry


def parse_raw_log_stream(raw_log_stream):
    for raw_log_entry in util.split_file(raw_log_stream, '\0'):
        log_entry = _parse_log_entry(raw_log_entry)
        if log_entry is not None:
            yield log_entry


def _parse_log_entry(raw_log_entry):
    """
    Parse a single git log entry into a LogEntry, or return None
    if it can't be parsed.
    """
    # A note on the encodings.  Git doesn't give us a way to get at
    # the encodings of the files / diffs (short of .gitattributes,
    # which has to be set by the original producers of the repo).  We
    # assume that the encoding is UTF-8, and just replace everything
    # else with that lovely question mark thing, to do the parsing /
    # manipulation, and then convert that utf-8 to unicode for the
    # returned LogEntry.
    utf8_log_entry = util.utf8(raw_log_entry)

    # attempt to split the header from the diff.
    split_log_entry = _split_entry_header(utf8_log_entry)
    if split_log_entry is None:
        return None
    header_lines, diff_lines = split_log_entry

    diff = '\n'.join(diff_lines)

    if not diff.strip():
        log.debug("Diff appeared to be empty.")
        return None

    author = _parse_header('Author: ', header_lines)
    if not author:
        log.debug("Could not parse author.")
        return None

    parsed_author = parse_name_and_email(author)
    if not parsed_author:
        log.debug("Could not parse author name / email.")
        return None
    author_name, author_email = parsed_author

    commit = _parse_header('commit ', header_lines)
    if not commit:
        log.debug("Could not parse commit.")
        return None

    log_msg = '\n'.join(_parse_log_msg(header_lines))

    return LogEntry(author_name=util.uc(author_name),
                    author_email=util.uc(author_email),
                    commit=util.uc(commit),
                    log_msg=util.uc(log_msg),
                    diff=util.uc(diff),
                    raw_log=raw_log_entry)


def _parse_log_msg(header_lines):
    """
    The log message begins with the first empty, and continues until
    the first non-empty line beginning with something other than a
    space character.

    Returns the log message lines as a list.
    """
    log_msg_lines = []
    for line in header_lines:
        if not line:
            log_msg_lines.append(line)
        elif line.startswith((' ', '\t')) and log_msg_lines:
            log_msg_lines.append(line)
        elif log_msg_lines:
            break
    return log_msg_lines


def _parse_header(header, header_lines):
    """
    Return the value of the header in header_lines, or None if it
    can't be found.

    Concession to git oddity: header should include everything to the
    trailing space of the header name (since, e.g., the format is
    'commit <hash>' but 'Author: <author>').
    """
    value = None
    for line in header_lines:
        if line.startswith(header):
            value = line.split(' ', 1)[1]
            break
    return value


def _split_entry_header(entry):
    """
    Parse `entry`, which is a single git log entry as unicode, diff
    and all, into a (header_lines, diff_lines) tuple, where
    header_lines is a list of unicodes including everything before the
    line beginning with 'diff', and diff_lines is a list of unicodes
    including everything from the diff line on.

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
        log.debug("Empty entry.")
        return None
    if not lines[0].startswith("commit"):
        log.debug("No commit line.")
        return None
    if not lines[1].startswith("Author"):
        log.debug("No author line.")
        return None
    # Start after the author line and look for the diff line.  This
    # should account for features like git notes.
    ind = 2
    lines_len = len(lines)
    while ind < lines_len and not lines[ind].startswith('diff'):
        ind += 1

    # call everything before the diff line the header, the rest
    # the diff.
    return lines[:ind], lines[ind:]
