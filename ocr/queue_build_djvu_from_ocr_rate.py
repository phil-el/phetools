#
# @file queue_ocr.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import sys
import os
from jobs import sge_jobs


def add_request(lang, filenames):
    job_req = {
        'jobname': 'build_djvu',
        'run_cmd': 'python',
        'force': True,
        'args': [
            os.path.expanduser('build_djvu_from_ocr_rate.py'),
            '-lang:' + lang,
            '-only_text',
        ],
        'max_vmem': 768,
    }

    for f in filenames:
        job_req['args'].append(f)

    db_obj = sge_jobs.DbJob()

    print job_req

    db_obj.add_request(**job_req)


def prepare_request(lang, filenames):
    print "preparing", lang, filenames
    for f in filenames:
        if not os.path.exists(f):
            print >> sys.stderr, "file:", f, "doesn't exist"
            exit(1)
    add_request(lang, filenames)


if __name__ == "__main__":
    filenames = []
    lang = None
    for arg in sys.argv[1:]:
        if arg.startswith('-lang:'):
            lang = arg[len('-lang:'):]
        else:
            filenames.append(arg)

    if not lang:
        print >> sys.stderr, "-lang: required"
        exit(1)

    prepare_request(lang, filenames)
