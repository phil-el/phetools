# -*- coding: utf-8 -*-

import os
import signal
import multiprocessing
import itertools

# helper function
def read_cpu_time():
    fd = open('/proc/stat', 'r')
    line = fd.readline()
    fd.close()
    return [ int(x) for x in line.split(' ')[2:] ]

last_data = read_cpu_time()

# return the idle time in [0-1] range
def idle_time():
    global last_data
    data = read_cpu_time()
    diff = [x - y for x, y in itertools.imap(None, data, last_data)]
    last_data = data
    sum_diff = sum(diff)
    if sum_diff:
        return diff[3] / float(sum_diff)
    else:
        # this can occur at startup because /proc/stat is polled too fast.
        return 0.0

def sanitize_thread_array(thread_array, silent):
    for i in range(len(thread_array) - 1, -1, -1):
        # for some unknow reason is_alive doesn't work
        if thread_array[i].exitcode != None:
            if not silent:
                print "deleting thread", thread_array[i].pid
            del thread_array[i]

class TaskScheduler:
    def __init__(self, alarm_time = 1, silent = False):
        self.running_thread = []
        self.paused_thread = []
        self.alarm_time = alarm_time
        self.silent = silent
        signal.signal(signal.SIGALRM, self)
        signal.alarm(self.alarm_time)

    # helper function, caller must ensure it exists at least two running thread
    # (at least one in fact but basically if you call it with only one you
    # you have no warranty than at least one process is running)
    def pause_process(self):
        if not self.silent:
            print "pausing:", self.running_thread[0].pid
        self.paused_thread.append(self.running_thread[0])
        os.killpg(os.getpgid(self.running_thread[0].pid), signal.SIGSTOP)
        del self.running_thread[0]

    # helper function, caller must ensure it exists at least one paused thread
    def wakeup_process(self):
        if not self.silent:
            print "wakeup:",  self.paused_thread[0].pid
        self.running_thread.append(self.paused_thread[0])
        os.killpg(os.getpgid(self.paused_thread[0].pid), signal.SIGCONT)
        del self.paused_thread[0]

    def __call__(self, a, b):
        sanitize_thread_array(self.running_thread, self.silent)
        sanitize_thread_array(self.paused_thread, self.silent)
        # a bit costly to not cache it but we support cpu hotplug
        nr_cpu = multiprocessing.cpu_count()
        nr_free_proc = idle_time() * nr_cpu
        if not self.silent:
            print "nr_running proc: %d, nr free_proc: %d" % (len(self.running_thread), nr_free_proc)
        if nr_free_proc > 0.5 and len(self.paused_thread):
            self.wakeup_process()
        elif nr_free_proc < 0.25 and len(self.running_thread) > 1:
            self.pause_process()
        elif len(self.paused_thread):
            self.pause_process()
            self.wakeup_process()
            # Now len(self.running_thread) >= 1

        signal.alarm(self.alarm_time)

    def job_started(self, t):
        os.setpgid(t.pid, 0)
        self.running_thread.append(t)
        # avoid to overload the box at startup
        self("", "")

    def reset_group(self, thread_array):
        for t in thread_array:
            if t.exitcode != None:
                os.setpgid(t.pid, os.getprgp())

    def reset_all_group(self):
        self.reset_group(self.paused_thread)
        self.reset_group(self.running_thread)

if __name__ == "__main__":


    def thread_func():
        print os.getpid()
        while True:
            pass

    def start_jobs(task_scheduler):
        thread_array = []
        for i in range(multiprocessing.cpu_count()):
            print "starting thread"
            t = multiprocessing.Process(target=thread_func, args=())
            t.daemon = True
            t.start()
            task_scheduler.job_started(t)
            thread_array.append(t)
        return thread_array

    t = TaskScheduler()

    thread_array = start_jobs(t)
    print len(thread_array)

    while True:
        for i in range(len(thread_array)):
            thread_array[i].join(0.1)
