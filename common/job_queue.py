# -*- coding: utf-8 -*-
#
# @file job_queue.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import thread
import time
from collections import deque
import copy
import utils

# A simple job queue serializable to filesytem.
# use: put() put() get() remove(), get() remove() must be paired, put()
# can occur between get/remove pair, copy_items() between a get/remove
# will contain the get() items, but serializing this class will always act
# as if a pending remove() has been done, so if the job thread handling
# a job crash, and the application restart the saved jobs will not contain
# the job that crashed the worker.
class JobQueue:
    def __init__(self, filename = None):
        # Deque has it's own lock but we need your own to copy item.
        self._lock = thread.allocate_lock()
        self._items = deque()
        if filename:
            self._load(filename)
        self._last = None

    def put(self, *args):
        with self._lock:
            self._items.appendleft(args)

    def remove(self):
        with self._lock:
            self._last= None

    def get(self):
        got_it = False
        while not got_it:
            with self._lock:
                if len(self._items):
                    data = self._items.pop()
                    got_it = True
            #if not got_it:
            #    time.sleep(0.5)
        self._last = data

        return data

    def copy_items(self, get_last = False):
        with self._lock:
            data = copy.copy(self._items)
            if get_last and self._last:
                data.append(self._last)
        data = [x for x in data]
        return data

    def save(self, filename):
        # no need of a lock here.
        items = self.copy_items()
        utils.save_obj(filename, items)

    def empty(self):
        with self._lock:
            return len(self._items) == 0

    def _load(self, filename):
        # no need of a lock here
        items = utils.load_obj(filename)
        items.reverse()
        for d in items:
            self.put(*d)

if __name__ == "__main__":
    import os

    def expect(func, data, *args):
        d = func(*args)
        if d != data:
            raise ValueError("expect: " + str(data) + ", found: " + str(d))

    def put_get_save_test():
        jobs = JobQueue()
        jobs.put(1, 2)
        jobs.put(3, 4)
        jobs.put(5, 6)
        expect(jobs.copy_items, [(5, 6), (3, 4), (1, 2)], True)
        a, b = jobs.get()
        expect(jobs.copy_items, [(5, 6), (3, 4)])
        expect(jobs.copy_items, [(5, 6), (3, 4), (1, 2)], True)
        items = jobs.copy_items(True)
        jobs.remove()
        expect(jobs.copy_items, [(5, 6), (3, 4)])
        expect(jobs.copy_items, [(5, 6), (3, 4)], True)
        jobs.save('test_job_queue.dat')
        expect(tuple, (1, 2), (a, b))
        expect(jobs.get, (3, 4))
        jobs = JobQueue('test_job_queue.dat')
        expect(jobs.copy_items, [(5, 6), (3, 4)])
        expect(jobs.copy_items, [(5, 6), (3, 4)], True)
        os.remove('test_job_queue.dat')

    def thread_test():
        last = 1000
        def thread1(jobs):
            for i in range(1, last+1):
                jobs.put(i)
        def thread2(jobs):
            for i in range(1, last):
                jobs.copy_items()
                jobs.get()

        jobs = JobQueue()
        thread.start_new_thread(thread1, (jobs, ))
        thread.start_new_thread(thread2, (jobs, ))

        jobs.get()
        while not jobs.empty():
            pass

    put_get_save_test()
    thread_test()
