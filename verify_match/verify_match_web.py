#!/usr/bin/python
# GPL V2, author phe

__module_name__ = "verify_match_daemon"
__module_version__ = "1.0"
__module_description__ = "verify match daemon"

import sys
sys.path.append('/data/project/phetools/phe/match_and_split')
sys.path.append('/data/project/phetools/phe/common')
import simple_redis_ipc

import os
import re
import thread
import time
import copy

import pywikibot
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
            title, codelang, user, t, request = queue[-1]
            got_it = True
        lock.release()

    return title, codelang, user, t, request

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

def do_match(mysite, maintitle, user, codelang):

    opt = verify_match.default_options()
    opt.site = mysite
    maintitle = maintitle.replace(u'_', u' ')

    if verify_match.main(maintitle, opt) != False:
        return ret_val(E_OK, "")
    return ret_val(E_ERROR, "unknown error")


verify_queue = []

def html_for_queue(queue):
    html = u''
    for i in queue:
        mtitle = i[0]
        codelang = i[1]
        try:
            msite = pywikibot.getSite(codelang, 'wikisource')
            page = pywikibot.Page(msite, mtitle)
            # FIXME: an exception occur here.
            path = msite.nice_get_address(page.title(asUrl = True))
            url = '%s://%s%s' % (msite.protocol(), msite.hostname(), path)
        except BaseException as e:
            import traceback
            print >> sys.stderr, str(e)
            print >> sys.stderr, traceback.format_exc()
            url = ""

        html += date_s(i[3])+' '+i[2]+" "+i[1]+" <a href=\""+url+"\">"+i[0]+"</a><br/>"
    return html

# title user lang t conn
def do_status(lock, queue):
    lock.acquire()
    queue = copy.copy(queue)
    lock.release()

    html = common_html.get_head(u'Verify match')
    html += u"<body><div>The robot is running.<br/><hr/>"
    html += u"<br/>%d jobs in verify match queue.<br/>" % len(queue)
    html += html_for_queue(queue)
    html += u'</div></body></html>'
    return html

def bot_listening(lock):

    print date_s(time.time())+ " START"

    try:
        while True:
            request = simple_redis_ipc.wait_for_request('verify_match_daemon')
            if not request:
                continue
            try:
                print request

                cmd = request['cmd']['cmd']
                title = request['cmd'].get('title', '')
                title = unicode(urllib.unquote(title.encode('utf-8')), 'utf-8')
                lang = request['cmd'].get('lang', '')
                user = request['cmd'].get('user', '')
            except:
                # FIXME: don't raise but return an error with the request as
                # error msg ?
                print "error", request
                raise

            t = time.time()
            user = user.replace(' ', '_')

            print (date_s(t) + " REQUEST " + user + ' ' + lang + ' ' + cmd + ' ' + title).encode('utf-8')

            if cmd == "verify":
                add_job(lock, verify_queue, (title, lang, user, t, request))
            elif cmd == 'status':
                html = do_status(lock, verify_queue)
                simple_redis_ipc.send_reply(request, html)
            else:
                simple_redis_ipc.send_reply(request, ret_val(E_ERROR, "unknown command: " + cmd))

    finally:
        print >> sys.stderr, "STOP"

def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])


def job_thread(lock, queue, func):
    while True:
        title, codelang, user, t, request = get_job(lock, queue)

        time1 = time.time()
        out = ''
        try:
            mysite = pywikibot.getSite(codelang, 'wikisource')
        except:
            out = ret_val(E_ERROR, "site error: " + repr(codelang))
            mysite = False

        if mysite:
            out = func(mysite, title, user, codelang)

        if request:
            simple_redis_ipc.send_reply(request, out)

        time2 = time.time()
        print (date_s(time2) + title + ' ' + user + " " + codelang + " (%.2f)" % (time2-time1)).encode('utf-8')

        remove_job(lock, queue)


if __name__ == "__main__":
    try:
        lock = thread.allocate_lock()
        ident = thread.start_new_thread(job_thread, (lock, verify_queue, do_match))
        bot_listening(lock)
    except KeyboardInterrupt:
        pywikibot.stopme()
        os._exit(1)
    finally:
        pywikibot.stopme()
