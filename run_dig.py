#!/usr/bin/env python

from ConfigParser import SafeConfigParser
from optparse import OptionParser
import re
import shlex
import sys
from textwrap import dedent

from archaeologit import util


def _write_to_stdout(str_or_unicode):
    """
    Write `str_or_unicode` to stdout, encoding to utf-8 if it's
    unicode.

    No extra newline is written.
    """
    sys.stdout.write(util.utf8(str_or_unicode))


def main(conf_fname, num_procs, use_cached_logs):
    # only import this here to avoid log messages on -h.
    from archaeologit.excavator import excavate
    config_parser = SafeConfigParser(allow_no_value=True)

    config_parser.read(conf_fname)

    project_dir = config_parser.get('dirs', 'project_dir')
    log_cache_dir = config_parser.get('dirs', 'log_cache_dir')

    interesting_res = []
    boring_res = []

    if 'interesting_res' in config_parser.sections():
        interesting_res = [re.compile(r[0])
                           for r
                           in config_parser.items('interesting_res')]

    if 'boring_res' in config_parser.sections():
        boring_res = [re.compile(r[0])
                      for r
                      in config_parser.items('boring_res')]

    fact_finders = []

    if 'fact_functions' in config_parser.sections():
        fact_finders.extend([f[0]
                             for f
                             in config_parser.items('fact_functions')])

    if 'fact_exes' in config_parser.sections():
        fact_finders.extend([shlex.split(e[0])
                             for e
                             in config_parser.items('fact_exes')])

    excavate(project_dir,
             log_cache_dir,
             interesting_fnames_res=interesting_res,
             boring_fnames_res=boring_res,
             fact_finders=fact_finders,
             summarizer=_write_to_stdout,
             num_procs=num_procs,
             use_cached_logs=use_cached_logs)


if __name__ == '__main__':
    usage = dedent("""\
                   %prog [options] conf_file

                   See the examples dir for sample conf files.\
                   """)

    parser = OptionParser(usage=usage)

    parser.add_option("--no-use-cached-logs",
                      help=dedent("""\
                                  Don't use cached logs for files (normally
                                  archaeologit will re-use cached logs between
                                  runs, as git log is the most expensive
                                  part of a run)\
                                  """),
                      action="store_false",
                      dest="use_cached_logs",
                      default=True)
    parser.add_option("--num-procs",
                      type="int",
                      default=1,
                      help=dedent("""\
                                  The number of procs to run in parallel
                                  for git log extraction and fact finding,
                                  defaults to 1\
                                  """),
                      dest="num_procs")

    (opts, args) = parser.parse_args()

    if len(args) != 1:
        parser.error("Exactly one config file is required.")

    main(conf_fname=args[0], num_procs=opts.num_procs,
         use_cached_logs=opts.use_cached_logs)
