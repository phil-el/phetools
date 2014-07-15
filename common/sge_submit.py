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
class _SgePoll:
    def __init__(self, job_base_name):
        self.qstat_poll = set()
        self.job_base_name = job_base_name
        # Passing "-j name*" to qstat make output much more verbose so jobs
        # filtering is done on a simple qstat -xml. FIXME: check the output
        # format of qstat, it'll nice to get a very short output with -xml,
        # as we only need to get the queued job name list.
        self.qstat_args = [ qstat, '-xml' ]

    def running_jobs(self):
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
                    self.qstat_poll.add(job_id)
                elem.clear()

        ls.wait()

class SgeSubmit(threading.Thread):
    def __init__(self, job_base_name, max_job):
        super(SgeSubmit, self).__init__()
        self.pending_jobs = job_queue.JobQueue()
        self.running_jobs = {}
        self._lock = threading.Lock()
        self.force_stop = False
        self._sge_poll = _SgePoll(job_base_name)
        self.job_base_name = job_base_name
        self.count = 0
        self.max_job = max_job
        self.log_dir = log_dir + job_base_name + '/'
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def add_job(self, dct_command):
        self.pending_jobs.put(dct_command)

    def submit_job(self):
        if not self.pending_jobs.empty():
            self.count += 1
            job_name = self.job_base_name + '_' + str(self.count)
            log_name = self.log_dir + job_name

            with self._lock:
                job = self.pending_jobs.get()
                self.running_jobs[job_name] = job

            args = [ jsub, '-b', 'y', '-l', 'h_vmem=1280M', '-N',  job_name, '-o', log_name + '.out', '-e', log_name + '.err' , '-v', 'LANG=en_US.UTF-8' ] + [ quote_arg(x) for x in job[0] ]
            print args
            ls = subprocess.Popen(args, stdin=None, stdout=subprocess.PIPE, close_fds = True)
            print ls.stdout.read()
            ls.wait()

    def empty(self):
        with self._lock:
            return self.pending_jobs.empty() and len(self.running_jobs) == 0

    def run(self):
        while True:
            if self.force_stop:
                break
            jobs = self._sge_poll.running_jobs()
            with self._lock:
                for name in self.running_jobs.keys():
                    if not name in jobs:
                        del self.running_jobs[name]
            if len(jobs) < self.max_job:
                self.submit_job()
            time.sleep(2)

if __name__ == "__main__":
    import os
    try:
        sge_submit = SgeSubmit('manual_hocr', 24)
        sge_submit.start()
        lst = [

            ]
        for f in lst:
            job = ('python', os.path.expanduser('~/manual_hocr.py'), f, 'fr', 'slow')
            sge_submit.add_job(job)
            time.sleep(1)

        while not sge_submit.empty():
            time.sleep(1)

        sge_submit.force_stop = True
        sge_submit.join()
    except KeyboardInterrupt:
        os._exit(1)
