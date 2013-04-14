#!/usr/bin/python
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
#    copyright phe at some dot where

__module_name__ = "verify_match_daemon"
__module_version__ = "1.0"
__module_description__ = "verify_match daemon"

import match_and_split_config as config

import os
import socket
import re
import thread
import time
import copy

import json
import wikipedia, pywikibot
import common_html
import verify_match
import urllib

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
            title, codelang, user, t, conn = queue[-1]
            got_it = True
        lock.release()

    return title, codelang, user, t, conn

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

def do_match(mysite, maintitle, user, codelang):

    opt = verify_match.default_options()
    opt.site = mysite
    maintitle = maintitle.replace(u'_', u' ')

    if verify_match.main(maintitle, opt) != False:
        return ret_val(E_OK, "")
    return ret_val(E_ERROR, "unknown error")


verify_queue = []

def html_for_queue(queue):
    html = ''
    for i in queue:
        mtitle = i[0].decode('utf-8')
        codelang = i[1]
        try:
            # FIXME: do not harcode the family
            msite = wikipedia.getSite(codelang, 'wikisource')
            page = wikipedia.Page(msite, mtitle)
            path = msite.nice_get_address(page.urlname())
            url = '%s://%s%s' % (msite.protocol(), msite.hostname(), path)
        except:
            url = ""
        html += date_s(i[3])+' '+i[2]+" "+i[1]+" <a href=\""+url+"\">"+i[0]+"</a><br/>"
    return html

# title user lang t conn
def do_status(lock, queue):
    lock.acquire()
    queue = copy.copy(queue)
    lock.release()

    html = common_html.get_head('Verify match')
    html += "<body><div>The robot is running.<br/><hr/>"
    html += "<br/>%d jobs in match queue.<br/>" % len(queue)
    html += html_for_queue(queue)
    html += '</div></body></html>'
    return html

def utf8_encode_dict(data):
    ascii_encode = lambda x: x.encode('utf-8')
    return dict(map(ascii_encode, pair) for pair in data.items())

def bot_listening(lock):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('', 12349))
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
    servername_filename = '/home/phe/public_html/verify_match.server'
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
                request = json.loads(data, object_hook=utf8_encode_dict)
                print request

                cmd = request['cmd']
                title = request.get('title', '')
                title = urllib.unquote(title)
                lang = request.get('lang', '')
                user = request.get('user', '')
            except:
                print "error", data
                conn.close()
                continue

            t = time.time()
            user = user.replace(' ', '_')

            print date_s(t) + " REQUEST " + user + ' ' + lang + ' ' + cmd + ' ' + title

            if cmd == "verify":
                add_job(lock, verify_queue, (title, lang, user, t, conn))
            elif cmd == 'status':
                html = do_status(lock, verify_queue)
                conn.sendall(html);
                conn.close()
            else:
                conn.sendall(json.dumps(ret_val(E_ERROR, "unknown command: " + cmd)));
                conn.close()

    finally:
        sock.close()
        print "STOP"

def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])


def job_thread(lock, queue, func):
    while True:
        title, codelang, user, t, conn = get_job(lock, queue)

        time1 = time.time()
        out = ''
        try:
            mysite = wikipedia.getSite(codelang, config.family)
        except:
            out = ret_val(E_ERROR, "site error: " + repr(codelang))
            mysite = False

        if mysite:
            wikipedia.setSite(mysite)
            print mysite, title
            title = title.decode('utf-8')
            user = user.decode('utf-8')
            out = func(mysite, title, user, codelang)

        if conn:
            conn.sendall(json.dumps(out))
            conn.close()

        time2 = time.time()
        print date_s(time2) + title.encode('utf-8') + ' ' + user.encode("utf8") + " " + codelang + " (%.2f)" % (time2-time1) + " " + str(out)

        remove_job(lock, queue)


if __name__ == "__main__":
    lock = thread.allocate_lock()
    thread.start_new_thread(job_thread, (lock, verify_queue, do_match))
    bot_listening(lock)
