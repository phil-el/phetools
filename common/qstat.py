# -*- coding: utf-8 -*-
#
# @file sge_submit.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import job_queue
import threading
import time
import subprocess
import xml.etree.ElementTree as etree
import os

qstat = '/usr/bin/qstat'
jsub = '/usr/bin/jsub'
# base dir for the log, the real log dir is log_dir + job_base_name + '/'
log_dir = os.path.expanduser('~/log/sge/')

def quote_arg(arg):
    return "'" + arg.replace("'", r"'\''") + "'"

# Intended to be used by SgeSumbit, not thread safe and polling throttle is
# implemented in SgeSubmit class.
class Qstat:
    def __init__(self, job_base_name):
        self.qstat_poll = set()
        self.job_base_name = job_base_name
        # Passing "-j name*" to qstat make output much more verbose so jobs
        # filtering is done on a simple qstat -xml. FIXME: check the output
        # format of qstat, it'll nice to get a very short output with -xml,
        # as we only need to get the queued job name list.
        self.qstat_args = [ qstat, '-xml' ]

    def qstat(self):
        self._poll()
        return self.qstat_poll

    def _poll(self):
        self.qstat_poll.clear()
        ls = subprocess.Popen(self.qstat_args, stdout=subprocess.PIPE, close_fds = True)
        for event, elem in etree.iterparse(ls.stdout):
            if event == 'end' and elem.tag == 'job_list':
                job_id = elem.find('JB_job_number').text
                job_name = elem.find('JB_name').text
                if job_name.startswith(self.job_base_name):
                    self.qstat_poll.add(int(job_id))
                elem.clear()

        ls.wait()

if __name__ == "__main__":
    print Qstat('').qstat()
