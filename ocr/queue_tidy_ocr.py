# -*- coding: utf-8 -*-
#
# @file queue_tidy_ocr.py
#
# @remark Copyright 2016 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie


import sys
import os
from jobs import sge_jobs

def add_tidy_ocr_request(lang, filename):
    job_req = {
        'jobname' : 'tidy_ocr',
        'run_cmd' : 'python',
        'force' : False,
        'args' : [
            os.path.expanduser('~/botpywi/tidy_ocr.py'),
            '-lang:' + lang,
            '-monochrome',
            '' + filename
            ],
        'max_vmem' : 2048,
        }

    db_obj = sge_jobs.DbJob()

    print job_req

    db_obj.add_request(**job_req)

def prepare_tidy_ocr_request(lang, filename):
    print "preparing", lang, filename
    add_tidy_ocr_request(lang, filename)

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

    for f in filenames:
        prepare_tidy_ocr_request(lang, f)
