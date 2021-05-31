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


def add_hocr_request(lang, sublang, filename):
    job_req = {
        'jobname': 'correct_ocr',
        'run_cmd': 'python',
        'force': True,
        'args': [
            os.path.expanduser('~/botpywi/correct_ocr.py'),
            '-lang:' + lang,
            '-auto',
            '' + filename
        ],
        'max_vmem': 2048,
    }

    if sublang:
        job_req['args'].append('-sublang:' + sublang),

    db_obj = sge_jobs.DbJob()

    print job_req

    db_obj.add_request(**job_req)


def prepare_ocr_request(lang, sublang, filename):
    print "preparing", lang, filename
    if not os.path.exists(filename):
        print >> sys.stderr, "file:", filename, "doesn't exist"
        exit(1)
    add_hocr_request(lang, sublang, filename)


if __name__ == "__main__":
    filenames = []
    sublang = None
    lang = None
    for arg in sys.argv[1:]:
        if arg.startswith('-lang:'):
            lang = arg[len('-lang:'):]
        elif arg.startswith('-sublang:'):
            sublang = arg[len('-sublang:'):]
        else:
            filenames.append(arg)

    if not lang:
        print >> sys.stderr, "-lang: required"
        exit(1)

    for f in filenames:
        prepare_ocr_request(lang, sublang, f)
