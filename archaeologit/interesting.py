"""
Functions for determining whether a file is interesting or not, based
on regexps.
"""


def is_interesting_fname(fname, interesting_res, boring_res):
    """
    Returns True if `fname` is interesting, and False if it's boring.

    If there are boring_res, then intresting_res acts as an override
    on boring_res, otherwise, interesting_res acts as a filter.

    In the absence of any res, all fnames are interesting.

    Both interesting_res and boring_res are lists of compiled
    regular expressions.
    """
    matches_interesting = any(i_re.match(fname) for i_re in interesting_res)
    matches_boring = any(ni_re.match(fname) for ni_re in boring_res)

    if boring_res:
        return not matches_boring or matches_interesting

    if interesting_res:
        return matches_interesting

    return True
