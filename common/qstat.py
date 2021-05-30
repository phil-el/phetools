# -*- coding: utf-8 -*-
#
# @file sge_submit.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import subprocess
import xml.etree.ElementTree as etree
import utils
import sys

qstat = '/usr/bin/qstat'


# Return an empty set if qstat fail.
def running_jobs(job_base_name):
    jobs = set()
    try:
        ls = subprocess.Popen([qstat, '-xml'], stdout=subprocess.PIPE,
                              close_fds=True)
        for event, elem in etree.iterparse(ls.stdout):
            if event == 'end' and elem.tag == 'job_list':
                job_id = elem.find('JB_job_number').text
                job_name = elem.find('JB_name').text
                if job_name.startswith(job_base_name):
                    jobs.add(int(job_id))
                elem.clear()

        ls.wait()
        if ls.returncode:
            print >> sys.stderr, 'qstat failed', ls.returncode
            print >> sys.stderr, 'RECOVER'
            jobs = set()
    except:
        utils.print_traceback()
        print >> sys.stderr, 'RECOVER'
        jobs = set()

    return jobs


if __name__ == "__main__":
    print running_jobs('')
