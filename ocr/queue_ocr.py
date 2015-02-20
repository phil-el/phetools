# -*- coding: utf-8 -*-
#
# @file queue_ocr.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import sys
import os
sys.path.append(os.path.expanduser('~/phe/jobs'))
import sge_jobs

def add_hocr_request(lang, filename):
    job_req = {
        'jobname' : 'ocr',
        'run_cmd' : 'python',
        'force' : True,
        'args' : [
            os.path.expanduser('~/phe/ocr/ocr_djvu.py'),
            '-lang:' + lang,
            '' + filename
            ],
        'max_vmem' : 2048,
        }

    db_obj = sge_jobs.DbJob()

    print job_req

    db_obj.add_request(**job_req)

def prepare_ocr_request(lang, filename):
    print "preparing", lang, filename
    if not os.path.exists(filename):
        print >> sys.stderr, "file:", filename, "doesn't exist"
        exit(1)
    add_hocr_request(lang, filename)

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
        prepare_ocr_request(lang, f)
