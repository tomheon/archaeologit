"""
Excavates a project in a git repo, searching for interesting facts
about lines or files and recording them.
"""

import cPickle
import errno
import multiprocessing
import Queue
import os
import shutil
import signal
import sys
import tempfile
import zipfile

from archaeologit.interesting import is_interesting_fname
from archaeologit import project, git_log, log, util

# Multiprocessing is broken, and won't keyboard interrupt properly if
# you do a get() on an async result without a timeout.  So we use a
# really long timeout.
REALLY_LONG_TIME = 1024 * 1024


def excavate(project_dir, output_dir,
             interesting_fnames_res, boring_fnames_res,
             fact_finders, num_procs):
    pool = multiprocessing.Pool(num_procs)

    project_dir = util.real_abs_path(project_dir)

    fnames_to_excavate = _interesting_fnames_in_proj(project_dir,
                                                     interesting_fnames_res,
                                                     boring_fnames_res)
    log.info("Found %d interesting fnames", len(fnames_to_excavate))
    log.debug("Interesting fnames: %s", fnames_to_excavate)

    log_z_fnames = _extract_logs(pool,
                                 fnames_to_excavate,
                                 project_dir,
                                 output_dir)

    facts_async_results = []
    for log_z_fname in log_z_fnames:
        facts_async_results.append(pool.apply_async(_find_facts,
                                                    (log_z_fname,)))

    for res in facts_async_results:
        print res.get(REALLY_LONG_TIME)

    pool.close()
    pool.join()


def _extract_logs(pool, fnames_to_excavate, project_dir, output_dir):
    log_async_results = [pool.apply_async(_extract_log,
                                          (fname, project_dir,
                                           output_dir))
                         for fname
                         in fnames_to_excavate]

    log_z_fnames = []

    for res in log_async_results:
        (rel_name, tmp_file) = res.get(REALLY_LONG_TIME)
        log_z_fname = os.path.join(output_dir, rel_name)
        util.ensure_containing_dir_exists(log_z_fname)
        shutil.copyfile(tmp_file, log_z_fname)
        print "Wrote logs for %s" % rel_name
        os.unlink(tmp_file)
        log_z_fnames.append(log_z_fname)

    return log_z_fnames


def _extract_log(fname, project_dir, output_dir):
    """
    Intended to be called in a separate process.
    """
    rel_name = util.rel_fname(project_dir, fname)
    named_tmp_file = tempfile.NamedTemporaryFile(delete=False)
    with git_log.raw_log_stream(fname) as raw_log_stream:
        shutil.copyfileobj(raw_log_stream, named_tmp_file)
    named_tmp_file.close()
    return (rel_name, named_tmp_file.name)


def _find_facts(fname):
    """
    Intended to be called in a separate process.
    """
    facts = []

    with open(fname, 'rb') as fil:
        for log_entry in git_log.parse_raw_log_stream(fil):
            facts.append(log_entry.commit)
            facts.append(log_entry.author_name)
    return facts


def _interesting_fnames_in_proj(project_dir, interesting_fnames_res,
                                boring_fnames_res):
    return [fname
            for fname
            in project.ls(project_dir)
            if is_interesting_fname(fname,
                                    interesting_fnames_res,
                                    boring_fnames_res)]
