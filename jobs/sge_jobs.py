# -*- coding: utf-8 -*-
#
# @file sge_jobs.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import sys
import os
sys.path.append(os.path.expanduser('~/phe/common'))
import utils
import json
import hashlib
import time
import MySQLdb
import subprocess
import qstat
import re
import db
import collections

jsub = '/usr/bin/jsub'

class DbJob(db.UserDb):
    def __init__(self):
        super(DbJob, self).__init__('sge_jobs')

        self.Accounting = collections.namedtuple('Accounting',
            [
             'qname',           'hostname',             'group',
             'owner',           'jobname',              'jobnumber',
             'account',         'priority',             'qsub_time',
             'start_time',      'end_time',             'failed',
             'exit_status',     'ru_wallclock',         'ru_utime',
             'ru_stime',        'ru_maxrss',            'ru_ixrss',
             'ru_ismrss',       'ru_idrss',             'ru_isrsst',
             'ru_minflt',       'ru_majflt',            'ru_nswap',
             'ru_inblock',      'ru_oublock',           'ru_msdsnd',
             'ru_msgrcv',       'ru_nsignals',          'ru_nvcsw',
             'ru_nivcsw',       'project',              'departement',
             'granted',         'slots',                'task',
             'cpu',             'mem',                  'io',
             'category',        'iow',                  'pe_taskid',
             'used_maxvmem',    'arid',                 'ar_submission_time'
             ])
        self.all_state = set(['pending', 'running', 'success', 'accounting',
                              'sge_fail', 'fail'])

    def get_job_table(self, state_filter, limit = 50, offset = 0):
        limit += 1
        data = []
        state_filter = state_filter.split('|')
        if state_filter:
            for s in state_filter[:]:
                if s != 'all' and s not in self.all_state:
                    state_filter.remove(s)
            state_filter = tuple(state_filter)

        if not state_filter:
            state_filter = tuple([ 'fail', 'pending', 'running' ])

        if 'all' in state_filter:
            state_filter = tuple([ x for x in self.all_state ])

        with db.connection(self):
            fmt_strs = ', '.join(['%s'] * len(state_filter))
            q = 'SELECT * FROM job WHERE job_state IN (' + fmt_strs + ') ORDER BY job_id DESC LIMIT %s OFFSET %s'
            #print >> sys.stderr, q % (state_filter + (limit, ) + (offset,))
            self.cursor.execute(q, state_filter + (limit, ) + (offset,))
            data = self.cursor.fetchall()

        has_next = True if len(data) == limit else False
        return data[:limit-1], has_next

    def get_accounting_table(self, limit = 50, offset = 0, job_ids = None):
        limit += 1
        data = []
        if not job_ids:
            job_ids = []
        if type(job_ids) != type([]):
            jobs_ids = [ job_ids ]
        with db.connection(self):
            q = 'SELECT * from accounting '
            if job_ids:
                fmt_strs = ', '.join(['%s'] * len(job_ids))
                q += 'WHERE job_id in (' + fmt_strs + ') '

            q += 'ORDER BY job_id DESC, sge_jobnumber DESC, sge_hostname LIMIT %s OFFSET %s'
            self.cursor.execute(q, tuple(job_ids) + (limit, ) + (offset,))
            data = self.cursor.fetchall()

        has_next = True if len(data) == limit else False
        return data[:limit-1], has_next

    def pending_request(self, limit = 16, offset = 0):
        data = []
        with db.connection(self):
            self.cursor.execute("SELECT * FROM job WHERE job_state='pending' LIMIT %s OFFSET %s",
                                [ limit, offset ])
            data = self.cursor.fetchall()

        return data

    def _add_request(self, jobname, run_cmd, args, max_vmem, cpu_bound, force):

        job_id = 0

        args = json.dumps(args)
        h = hashlib.sha1()
        h.update(run_cmd + args)
        sha1 = h.hexdigest()

        q = 'SELECT * FROM job WHERE job_sha1 = %s'
        self.cursor.execute(q, [sha1])
        num = self.cursor.fetchone()

        if num:
            job_id = num['job_id']
        if num and not num['job_state'] in [ 'pending', 'running', 'accounting' ]:
            q = 'SELECT COUNT(*) FROM accounting WHERE job_id=%s'
            self.cursor.execute(q, [ job_id ])
            count = self.cursor.fetchone()['COUNT(*)']
            if count < 3 or force:
                q = 'UPDATE job SET job_state="pending" WHERE job_id=%s'
                self.cursor.execute(q, [ job_id ] )
            else:
                print >> sys.stderr, "Job %d reached its max try count, rejected" % job_id, args
        elif not num:
            job_data = {
                'job_sha1' : sha1,
                'job_jobname' : jobname,
                'job_cpu_bound' : cpu_bound,
                'job_submit_time' : int(time.time()),
                'job_run_cmd' : run_cmd,
                'job_log_dir' : os.path.expanduser('~/log/sge/'),
                'job_args' : args,
                'job_state' : 'pending',
                'job_max_vmem' : max_vmem,
                }

            add_job_field = '(' + ', '.join(job_data.keys()) + ') '

            # Quoting is done by execute so it's secure.
            add_job_value_list = [ '%%(%s)s' % k for k in job_data.keys() ]
            add_job_value = 'VALUE (' + ', '.join(add_job_value_list) + ')'

            add_job = ('INSERT INTO job ' + add_job_field + add_job_value)

            self.cursor.execute(add_job, job_data)

            self.cursor.execute('SELECT LAST_INSERT_ID()')
            job_id = self.cursor.fetchone()['LAST_INSERT_ID()']

        return job_id

    def add_request(self, jobname, run_cmd, args,  max_vmem,
                    cpu_bound = True, force = False):
        job_id = 0
        with db.connection(self):
            job_id = self._add_request(jobname, run_cmd, args,
                                       max_vmem, cpu_bound, force)
        return job_id

    def exec_request(self, r):
        sge_job_nr = 0

        cmdline_arg = job_cmdline_arg(r, 'job_run_cmd')
        sge_cmdline = sge_cmdline_arg(r)
        ls = subprocess.Popen(sge_cmdline + cmdline_arg,
                              stdin=None, stdout=subprocess.PIPE,
                              close_fds = True)
        text = ls.stdout.read()
        ls.wait()
        try:
            sge_job_nr = int(re.search('Your job (\d+) ', text).group(1))
            new_state = 'running'
        except:
            utils.print_traceback("sge failure to exec job: %d" % r['job_id'], text)
            new_state = 'sge_fail'


        with db.connection(self):
            q = 'UPDATE job SET job_state=%s, sge_jobnumber=%s WHERE job_id=%s'
            self.cursor.execute(q, [ new_state, sge_job_nr, r['job_id'] ])

    def run_batch(self, nr_running, limit = 16):
        max_to_run = max(min(limit - nr_running, limit), 0)
        if max_to_run:
            for r in self.pending_request(max_to_run):
                print "starting:", r
                self.exec_request(r)

    def _exec_check(self, request):
        q = 'UPDATE job SET job_state="accounting" WHERE job_id=%s'
        self.cursor.execute(q, [ request['job_id'] ])

        q = 'INSERT into accounting (job_id, sge_jobnumber) VALUE (%s, %s)'
        self.cursor.execute(q, [ request['job_id'], request['sge_jobnumber'] ])

        self.conn.commit()

    def check_running(self):
        sge_running = qstat.running_jobs('')
        if sge_running:
            with db.connection(self):
                q = 'SELECT job_id, sge_jobnumber, job_args FROM job WHERE job_state="running"'
                self.cursor.execute(q)
                for r in self.cursor.fetchall():
                    if not r['sge_jobnumber'] in sge_running:
                        self._exec_check(r)
            return len(sge_running)
        return None

    # Limiting is necessary because a job can be finished but not yet in the
    # accouting file (cache effect) so we can easily scan the whole file. To
    # avoid that we limit the backward search to two days by default.
    # float is allowed so last_time_day = 1.0/24 is an hour.
    def search_accounting(self, jobs, last_time_day = 2):
        last_time_day = max(1.0/24, last_time_day)
        now = int(time.time())
        count = 0
        nr_job = len(jobs)
        for line in utils.readline_backward('/data/project/.system/accounting'):
            accounting = self.Accounting(*line.split(':'))
            jobnumber = int(accounting.jobnumber)
            count += 1
            if jobnumber in jobs:
                jobs[jobnumber].append(accounting)
                nr_job -= 1
                if nr_job == 0:
                    print "breaking after %d line" % count
                    break

            # end_time == 0 occur when sge failed to start a task, don't
            # use it to get the elapsed time between end_time and now.
            if int(accounting.end_time) and now - int(accounting.end_time) >= last_time_day * 86400:
                print "breaking after %d line, TIMEOUT" % count
                break

    def update_accounting(self):
        jobs = {}  
        with db.connection(self):
            q = 'SELECT job_id, sge_jobnumber, sge_hostname FROM accounting WHERE sge_hostname=""'
            self.cursor.execute(q)
            for data in self.cursor.fetchall():
                jobs[data['sge_jobnumber']] = [ data ]

        if not len(jobs):
            return

        self.search_accounting(jobs)

        with db.connection(self):
            fields = [ 'hostname', 'qsub_time', 'start_time', 'end_time',
                       'failed', 'exit_status', 'ru_utime', 'ru_stime',
                       'ru_wallclock', 'used_maxvmem' ]

            set_str = []
            for f in fields:
                set_str.append('sge_%s=%%(%s)s' % (f, f))
            set_str = ', '.join(set_str)
            for sge_jobnumber in jobs:
                sge_jobnumber = int(sge_jobnumber)

                # Accounting not found, it'll found in the next run.
                if len(jobs[sge_jobnumber]) <= 1:
                    continue
                q  = "UPDATE accounting SET " + set_str
                # We can't let execute() do the quoting for jobnumber, but 
                # sge_jobnumber is forced to int so this code is sql injection
                # safe.
                q += ' WHERE sge_jobnumber=%d' % sge_jobnumber
                # Kludge, execute() don't accept a namedtuple nor an
                # OrderedDict so convert it explicitly to a dict.
                d = jobs[sge_jobnumber][1]._asdict()
                d = dict(zip(d.keys(), d.values()))
                self.cursor.execute(q, d)

                job = jobs[sge_jobnumber][0]

                new_state = 'success'
                if int(d['failed']) or int(d['exit_status']):
                    new_state = 'fail'
                q = 'UPDATE job SET job_state=%s WHERE job_id=%s'
                self.cursor.execute(q, [ new_state, job['job_id'] ])

def quote_arg(arg):
    return "'" + arg.replace("'", r"'\''") + "'"

def job_cmdline_arg(request, cmd):
    cmd_arg  = [ request[cmd] ]
    cmd_arg += [ quote_arg(x) for x in json.loads(request['job_args']) ]
    return cmd_arg

def sge_cmdline_arg(request):
    job_name = request['job_jobname']
    log_name = request['job_log_dir'] + job_name + '_' + str(request['job_id'])
    sge_cmd_arg = [
        jsub,
        '-b', 'y',
        '-l', 'h_vmem=%dM' % request['job_max_vmem'],
        '-N',  job_name,
        '-o', log_name + '.out', '-e', log_name + '.err' ,
        '-v', 'LANG=en_US.UTF-8'
        ]

    if request.has_key('working_dir'): # always Fase atm, for future use.
        sge_cmd_arg.append('-wd')
        sge_cmd_arg.append(request['working_dir'])
    else:
        sge_cmd_arg.append('-wd')
        sge_cmd_arg.append(os.path.expanduser('~/botpywi'))

    return sge_cmd_arg

if __name__ == "__main__":

    db_job = DbJob()

    db_job.update_accounting()

    nr_running = db_job.check_running()

    print "running task:", nr_running

    if nr_running:
        db_job.run_batch(nr_running, limit = 24+5)
