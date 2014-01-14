"""
Excavates a project in a git repo, searching for interesting facts
about lines or files and recording them.
"""

import multiprocessing
import os
import shutil
import tempfile

from archaeologit.interesting import is_interesting_fname
from archaeologit import project, git_log, log, util

# Multiprocessing is broken, and won't keyboard interrupt properly if
# you do a get() on an async result without a timeout.  So we use a
# really long timeout.
REALLY_LONG_TIME = 1024 * 1024


def excavate(project_dir, log_cache_dir,
             interesting_fnames_res,
             boring_fnames_res,
             fact_finders, summarizer, num_procs=1,
             use_cached_logs=True):
    """
    Extract the git logs for all the interesting files in
    `project_dir`, running each file's logs through all the supplied
    `fact_finders` and passing the generated facts into the supplied
    `summarizer`.

    If `summarizer` is None, the facts will be printed to standard
    out.

    - `project_dir`: the root directory of the project to excavate

    - `log_cache_dir`: the directory where the null terminated git logs
      will be written for later fact finding

    - `interesting_fnames_res`: the regular expressions that will be
      passed to is_interesting_fname to determine whether a given file
      in the project is interesting

    - `boring_fnames_res`: the regular expressions that will be passed
      to is_interesting_fname to determine whether a given file in the
      project is interesting

    - `fact_finders`: a list whose elements are either strs or lists
      of strs, each str representing a fully qualified function named
      (e.g. 'one.two.func'), which must be importable (i.e. somewhere
      in the python path), and each list of strs representing an
      external exe to invoke.

      For each log entry of each interesting file in the project dir,
      a function will be passed (fname, log_entry), where fname is the
      name of the file relative to project dir, and log_entry is a
      git_log.LogEntry named tuple.

      An external exe will receive the fname and fields of the
      log_entry on stdin, separated by null bytes.  The fields will
      appear in the same order they are declared in git_log.LogEntry.

      It is guaranteed that for a given fname, each log entry will be
      passed to the fact finders in chronological order, in the same
      process.

      The fact finders can return anything that can be serialized
      across python processes, but note that if you provide a
      `summarizer`, the summarizer must handle whatever a fact finder
      might return, and if you do not provide a summarizer, whatever
      the fact finders return must be sensibly printable to stdout.

    - `summarizer`: a callable that will be called repeatedly, once
      for each generated fact

    - `num_procs`: how many parallel processes to use when generating
      logs and facts.  Note that the logs are generated with calls to
      'git', and are relatively CPU and disk intensive.  Generally you
      can up this number until you're maxing out your disk, past which
      you won't see performance improvements.

    Returns `summarizer`.
    """
    pool = multiprocessing.Pool(num_procs)

    project_dir = util.real_abs_path(project_dir)

    fnames_to_excavate = _interesting_fnames_in_proj(project_dir,
                                                     interesting_fnames_res,
                                                     boring_fnames_res)
    log.info("Found %d interesting fnames", len(fnames_to_excavate))
    log.debug("Interesting fnames: %s", fnames_to_excavate)

    rel_and_log_z_fnames = _extract_logs(pool,
                                         fnames_to_excavate,
                                         project_dir,
                                         log_cache_dir,
                                         use_cached_logs)

    facts_async_results = []
    for (rel_name, log_z_fname) in rel_and_log_z_fnames:
        facts_async_results.append(pool.apply_async(_find_facts,
                                                    (rel_name,
                                                     log_z_fname,
                                                     fact_finders)))

    for res in facts_async_results:
        facts = res.get(REALLY_LONG_TIME)
        for fact in facts:
            summarizer(fact)

    pool.close()
    pool.join()

    return summarizer


def _extract_logs(pool, fnames_to_excavate, project_dir, log_cache_dir,
                  use_cached_logs):
    """
    For each fname in `fnames_to_excavate` under `project_dir`,
    extract the git logs, writing them to a shadowed file hierarchy
    under `log_cache_dir`.

    The logs are extracted from git in parallel using the supplied
    `pool`.

    Returns a list of tuples of (fname_relative_to_project_dir,
    path_to_log_file) where path_to_log_file is the path to a file
    containing a null-byte delimited series of git logs for the fname.
    """

    rel_and_log_z_fnames = []
    log_async_results = []

    for fname in fnames_to_excavate:
        rel_name = util.rel_fname(project_dir, fname)
        log_z_fname = os.path.join(log_cache_dir, rel_name)
        rel_and_log_z_fnames.append((rel_name, log_z_fname))
        if _should_get_log(log_z_fname, use_cached_logs):
            log_async_results.append(pool.apply_async(_extract_log,
                                                      (fname, project_dir)))

    for res in log_async_results:
        (rel_name, tmp_file) = res.get(REALLY_LONG_TIME)
        log_z_fname = os.path.join(log_cache_dir, rel_name)
        util.ensure_containing_dir_exists(log_z_fname)
        shutil.copyfile(tmp_file, log_z_fname)
        log.info("Wrote logs for %s" % rel_name)
        os.unlink(tmp_file)

    return rel_and_log_z_fnames


def _should_get_log(log_z_fname, use_cached_logs):
    if not use_cached_logs:
        return True
    return not os.path.exists(log_z_fname)


def _extract_log(fname, project_dir):
    """
    Extract the git log for `fname` under `project_dir`, writing the
    null byte delimited entries to a temp file.

    Returns fname as relative to project_dir, and the name of the temp
    file.

    Intended to be called in a separate process as a target of
    apply_async.
    """
    rel_name = util.rel_fname(project_dir, fname)
    named_tmp_file = tempfile.NamedTemporaryFile(delete=False)
    with git_log.raw_log_stream(fname) as raw_log_stream:
        shutil.copyfileobj(raw_log_stream, named_tmp_file)
    named_tmp_file.close()
    return (rel_name, named_tmp_file.name)


def _find_facts(fname, log_z_fname, fact_finders):
    """
    Intended to be called in a separate process.

    - `fname`: the name of the source file whose logs should be
      plumbed for facts, relative to the project dir

    - `log_z_fname`: the full path to the file where the null byte
      delimited git logs for the file have been written

    - `fact_finders`: a list of strs and lists of strs, each
      describing a fact finding function to call (in the case of strs)
      or an external process to invoke (in the case of the lists of
      strs) on each entry in the log
    """
    log.info("Findings facts for %s" % fname)

    facts = []
    finders = [_funcify_fact_finder(f) for f in fact_finders]

    with open(log_z_fname, 'rb') as fil:
        for log_entry in git_log.parse_raw_log_stream(fil):
            for finder in finders:
                facts.append(finder(fname, log_entry))

    return facts


def _funcify_fact_finder(list_or_str):
    """
    Return a function that will invoke the fact finder described by
    list_or_str.

    If list_or_str is a list, it's assumed to refer to an external
    process that should be invoked, and this will return a function
    that will invoke that process and pass the arguments to its stdin,
    returning the process's stdout as a str.

    If list_or_str is a str, it's assumed to be a fully qualified name
    of a function to load (e.g. 'one.two.func').
    """
    if isinstance(list_or_str, list):
        def _wrap(fname, log_entry):
            with tempfile.TemporaryFile() as fil:
                fil.write('\0'.join([util.utf8(x)
                                     for x
                                     in [fname] + list(log_entry)]))
                fil.flush()
                fil.seek(0)
                with util.wrap_popen(list_or_str, stdin_fil=fil) as out_fil:
                    return out_fil.read()
        return _wrap
    else:
        return util.funcify(list_or_str)


def _interesting_fnames_in_proj(project_dir, interesting_fnames_res,
                                boring_fnames_res):
    """
    Return a list of the interesting fnames in the project dir, using
    the logic of interesting.is_interesting_fname.
    """
    interesting_fnames = []

    for fname in project.ls(project_dir):
        rel_fname = util.rel_fname(project_dir, fname)
        if is_interesting_fname(rel_fname,
                                interesting_fnames_res,
                                boring_fnames_res):
            interesting_fnames.append(fname)
        else:
            log.info("Skipping fname %s, not interesting" % fname)

    return interesting_fnames
