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


def add_ocr_request(lang, filename):
    job_req = {
        'jobname': 'ocr',
        'run_cmd': 'python',
        'force': True,
        'args': [
            os.path.expanduser('~/phe/ocr/ocr_djvu.py'),
            '-lang:' + lang,
            '' + filename
        ],
        'max_vmem': 2048,
    }

    db_obj = sge_jobs.DbJob()

    print(job_req)

    db_obj.add_request(**job_req)


def prepare_ocr_request(lang, filename):
    print("preparing", lang, filename)
    if not os.path.exists(filename):
        print("file:", filename, "doesn't exist", file=sys.stderr)
        exit(1)
    add_ocr_request(lang, filename)


if __name__ == "__main__":
    filenames = []
    lang = None
    for arg in sys.argv[1:]:
        if arg.startswith('-lang:'):
            lang = arg[len('-lang:'):]
        else:
            filenames.append(arg)

    if not lang:
        print("-lang: required", file=sys.stderr)
        exit(1)

    for f in filenames:
        prepare_ocr_request(lang, f)
