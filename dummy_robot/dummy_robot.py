#!/usr/bin/python
# GPL V2, author phe

__module_name__ = "dummy_robot"
__module_version__ = "1.0"
__module_description__ = "dummy robot"

import sys
sys.path.append('/data/project/phetools/phe/common')
import simple_redis_ipc
import common_html

import os
import thread
import time
import copy
import urllib

E_ERROR = 1
E_OK = 0

# FIXME: use a real Queue object and avoid polling the queue

# Get a job w/o removing it from the queue. FIXME: probably not the best
# way, if a job can't be handled due to exception and the exception is
# gracefully catched by the worker thread, there is no warranty than the
# job will be removed from the queue, so the worker thread can hang forever
# trying to do something causing an exception. This is not possible actually
# but it's fragile to not remove the job when getting it.
def get_job(lock, queue):
    got_it = False
    while not got_it:
        time.sleep(0.5)
        lock.acquire()
        if queue != []:
            title, t, request = queue[-1]
            got_it = True
        lock.release()

    return title, t, request

def remove_job(lock, queue):
    lock.acquire()
    queue.pop()
    lock.release()

def add_job(lock, queue, cmd):
    lock.acquire()
    queue.insert(0, cmd)
    lock.release()

def ret_val(error, text):
    if error:
        print >> sys.stderr, "Error: %d, %s" % (error, text)
    return  { 'error' : error, 'text' : text }

def do_exec(title, request):
    if request['cmd']['cmd'] == 'timeout':
        time.sleep(60)
        return ret_val(E_ERROR, "timeout: 60 sec: " + title)

    return ret_val(E_OK, "exec ok: " + title)

robot_queue = []

def html_for_queue(queue):
    html = u''
    for i in queue:
        mtitle = i[0]

        html += date_s(i[1]) + ' ' + mtitle + "<br/>"
    return html

# title t requestn
def do_status(lock, queue):
    lock.acquire()
    queue = copy.copy(queue)
    lock.release()

    html = common_html.get_head(u'Dummy robot')
    html += u"<body><div>The robot is running.<br/><hr/>"
    html += u"<br/>%d jobs in dummy robot queue.<br/>" % len(queue)
    html += html_for_queue(queue)
    html += u'</div></body></html>'
    return html

def bot_listening(lock):

    print date_s(time.time()) + " START"

    try:
        while True:
            request = simple_redis_ipc.wait_for_request('dummy_robot')
            if not request:
                continue

            try:
                print request

                cmd = request['cmd']['cmd']
                title = request['cmd'].get('title', '')
                title = unicode(urllib.unquote(title.encode('utf-8')), 'utf-8')
            except:
                ret = ret_val(E_ERROR, "invalid request")
                simple_redis_ipc.send_reply(request, ret)
                continue

            t = time.time()

            print (date_s(t) + " REQUEST " + cmd + ' ' + title).encode('utf-8')

            if cmd in [ "exec", "timeout" ]:
                add_job(lock, robot_queue, (title, t, request))
            elif cmd == 'status':
                html = do_status(lock, robot_queue)
                simple_redis_ipc.send_reply(request, html)
            elif cmd == 'ping':
                simple_redis_ipc.send_reply(request, ret_val(E_OK, 'pong'))
            else:
                simple_redis_ipc.send_reply(request, ret_val(E_ERROR, "unknown command: " + cmd))

    finally:
        print >> sys.stderr, "STOP"

def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])


def job_thread(lock, queue, func):
    while True:
        title, t, request = get_job(lock, queue)

        time1 = time.time()

        out = func(title, request)

        if request:
            simple_redis_ipc.send_reply(request, out)

        time2 = time.time()
        print (date_s(time2) + ' ' + title + " (%.2f)" % (time2-time1)).encode('utf-8')

        remove_job(lock, queue)


if __name__ == "__main__":
    try:
        lock = thread.allocate_lock()
        thread.start_new_thread(job_thread, (lock, robot_queue, do_exec))
        bot_listening(lock)
    except KeyboardInterrupt:
        pywikibot.stopme()
        os._exit(1)
#    finally:
#        pywikibot.stopme()
