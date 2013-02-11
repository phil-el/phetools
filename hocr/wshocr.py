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

def ret_val(error, text):
    if error:
        print "Error: %d, %s" % (error, text)
    return  { 'error' : error, 'text' : text }

def do_get(page, user, codelang):
    base_dir = '/mnt/user-store/phe/cache/hocr/%s/%s/%s/%s/%d'
    h = hashlib.md5()
    h.update(page.encode('utf-8'))
    h = h .hexdigest()
    page_nr = re.sub(u'.*/([0-9]+)$', u'\\1', page)

    try:
        page_nr = int(page_nr)
    except:
        return ret_val(E_ERROR, "unable to extract page number from page=")

    filename = base_dir % (h[0:2], h[2:4], h[4:6], h[6:], page_nr)

    if not os.path.exists(filename):
        return ret_val(E_ERROR, "unable to locate file for page %s" % page.encode('utf-8'))

    fd = open(filename)
    text = fd.read()
    fd.close()

    #return ret_val(E_ERROR, "test: %s %s %s %s %s" %(page, user, codelang, h, filename))
    return ret_val(E_OK, text)


get_queue = []

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
    m_queue = copy.deepcopy(get_queue)
    lock.release()

    html = common_html.get_head('hOCR server status')

    html += "<body><div>the robot is running.<br/><hr/>"
    html += "<br/>%d jobs queued.<br/>" % len(m_queue)
    html += html_for_queue(m_queue)
    html += '</div></body></html>'

    conn.send(html)
    conn.close()


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
                add_job(lock, get_queue, (page, lang, user, t, conn))
            else:
                out = ret_val(E_ERROR, "unknown command: " + cmd)
                conn.send(json.dumps(out));
                conn.close()

    finally:
        sock.close()
        print "STOP"

        for i in range(len(get_queue)):
            page, lang, user, t, conn = get_queue[i]
            get_queue[i] = (page, lang, user, t, None)
            if conn:
                conn.close()

        f = open("wshocr.job","w")
        f.write(repr(get_queue))
        f.close()


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
            conn.close()

        time2 = time.time()
        print date_s(time2), page.encode('utf-8'), user.encode("utf8"), codelang, " (%.2f)" % (time2-time1), out

        remove_job(lock, queue)


if __name__ == "__main__":
    try:
        f = open("wshocr.job","r")
        jobs = f.read()
        f.close()
        gq = eval(jobs)
        for i in gq:
            print i
            get_queue.append(i)
    except:
        pass

    lock = thread.allocate_lock()
    thread.start_new_thread(job_thread, (lock, get_queue, do_get))
    bot_listening(lock)
