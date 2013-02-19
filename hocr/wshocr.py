#!/usr/bin/python
# -*- coding: utf-8 -*-
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
#
#    copyright phe @ nowhere

__module_name__ = "wshocr"
__module_version__ = "1.0"
__module_description__ = "wikisource hocr server"

import os
import socket
import re
import thread
import time
import copy
import json
import common_html
import hashlib
import gzip
import common
import signal

mylock = thread.allocate_lock()

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
            page, codelang, user, t, conn = queue[-1]
            got_it = True
        lock.release()

    return page, codelang, user, t, conn

def remove_job(lock, queue):
    lock.acquire()
    queue.pop()
    lock.release()

def add_job(lock, queue, cmd):
    lock.acquire()
    queue.insert(0, cmd)
    lock.release()

def cache_path(book_name):

    book_name = book_name.replace(u'_', u' ')

    base_dir  = '/mnt/user-store/phe/cache/hocr/'
    base_dir += '%s/%s/%s/%s/'

    h = hashlib.md5()
    h.update(book_name.encode('utf-8'))
    h = h.hexdigest()

    base_dir = base_dir % (h[0:2], h[2:4], h[4:6], h[6:])

    return base_dir

def ret_val(error, text):
    if error:
        print "Error: %d, %s" % (error, text)
    return  { 'error' : error, 'text' : text }

def do_get(page, user, codelang):
    page_nr = re.sub(u'^.*/([0-9]+)$', u'\\1', page)
    try:
        page_nr = int(page_nr)
    except:
        return ret_val(E_ERROR, "unable to extract page number from page=")

    book_name = re.sub(u'^(.*)/[0-9]+$', u'\\1', page)

    base_dir = cache_path(book_name)

    filename = base_dir + 'page_%04d.html' % page_nr

    if os.path.exists(filename + '.gz'):
        fd = gzip.open(filename + '.gz')
    elif os.path.exists(filename):
        fd = open(filename)
    else:
        return ret_val(E_ERROR, "unable to locate file %s for page %s" % (filename, page.encode('utf-8')))

    text = fd.read()
    fd.close()

    return ret_val(E_OK, text)

jobs = None

def html_for_queue(queue):
    html = ''
    for i in queue:
        mtitle = i[0].decode('utf-8')
        codelang = i[1]
        try:
            msite = wikipedia.getSite(codelang, 'wikisource')
            page = wikipedia.Page(msite, mtitle)
            path = msite.nice_get_address(page.urlname())
            url = '%s://%s%s' % (msite.protocol(), msite.hostname(), path)
        except:
            url = ""
        html += date_s(i[4])+' '+i[2]+" "+i[1]+" <a href=\""+url+"\">"+i[0]+"</a><br/>"
    return html

def do_status(lock, conn):
    lock.acquire()
    m_queue = copy.deepcopy(jobs['get_queue'])
    lock.release()

    html = common_html.get_head('hOCR server status')

    html += "<body><div>the robot is running.<br/><hr/>"
    html += "<br/>%d get request queued.<br/>" % len(m_queue)
    html += html_for_queue(m_queue)
    html += "<br/>%(number_of_get_job)d get since server start<br/>" % jobs
    html += '</div></body></html>'

    conn.send(html)
    conn.close()

def stop_queue(queue):
    for i in range(len(queue)):
        page, lang, user, t, conn = queue[i]
        queue[i] = (page, lang, user, t, None)
        if conn:
            conn.close()

# either called through a SIGUSR2 or a finally clause.
def on_exit(sign_nr, frame):
        print "STOP"

        # no value to save the get queue but conn must be closed first
        stop_queue(jobs['get_queue'])
        jobs['get_queue'] = []

        common.save_obj("wshocr.jobs", jobs)

def bot_listening(lock):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('', 12348))
    except:
        print "could not start listener : socket already in use"
        thread.interrupt_main()
        return

    print date_s(time.time())+ " START"
    sock.listen(1)
    sock.settimeout(None)

    # The other side needs to know the server name where the daemon run to open
    # the connection. We write it after bind() because we want to ensure than
    # only one instance of the daemon is running. FIXME: this is not sufficient
    # if the job is migrated so migration is disabled for this daemon.
    servername_filename = os.getenv('HOME') + '/public_html/hocr_server.server'
    if os.path.exists(servername_filename):
        os.chmod(servername_filename, 0644)
    fd = open(servername_filename, "w")
    fd.write(socket.gethostname())
    fd.close()
    os.chmod(servername_filename, 0444)

    try:
        while True:
            conn, addr = sock.accept()
            data = conn.recv(1024)
            try:
                cmd, page, lang, user = data.split('|')
            except:
                print "error", data
                conn.close()
                continue

            t = time.time()
            user = user.replace(' ', '_')

            print date_s(t) + " REQUEST " + user + ' ' + lang + ' ' +  cmd + ' ' + page

            if cmd == "status":
                do_status(lock, conn)
            elif cmd == "get":
                jobs['number_of_get_job'] += 1
                add_job(lock, jobs['get_queue'], (page, lang, user, t, conn))
            else:
                out = ret_val(E_ERROR, "unknown command: " + cmd)
                conn.send(json.dumps(out));
                conn.close()

    finally:
        sock.close()
        on_exit(0, None)

def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])

def job_thread(lock, queue, func):
    while True:
        page, codelang, user, t, conn = get_job(lock, queue)

        time1 = time.time()
        out = ''

        print page, user
        page = page.decode('utf-8')
        user = user.decode('utf-8')
        out = func(page, user, codelang)

        if conn:
            conn.send(json.dumps(out))
            #conn.send(out["text"])
            conn.close()

        time2 = time.time()
        print date_s(time2), page.encode('utf-8'), user.encode("utf8"), codelang, " (%.2f)" % (time2-time1)

        remove_job(lock, queue)

def default_jobs():
    return {
        'get_queue' : [],
        'number_of_get_job' : 0
        }

if __name__ == "__main__":
    # qdel send a SIGUSR2 if -notify is used when starting the job.
    signal.signal(signal.SIGUSR2, on_exit)
    try:
        jobs = common.load_obj("wshocr.jobs")
    except:
        jobs = default_jobs()

    lock = thread.allocate_lock()
    thread.start_new_thread(job_thread, (lock, jobs['get_queue'], do_get))
    bot_listening(lock)
