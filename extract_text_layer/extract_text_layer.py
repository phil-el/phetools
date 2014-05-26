#!/usr/bin/python
# GPL V2, author phe                                                            
__module_name__ = "extract_text_layer_daemon"
__module_version__ = "1.0"
__module_description__ = "extract text layer daemon"


import sys
sys.path.append('/data/project/phetools/phe/match_and_split')
sys.path.append('/data/project/phetools/phe/common')
import simple_redis_ipc
import lifo_cache

import os
import socket
import re
import thread
import time
import copy

import align
import pywikibot
import urllib
import common_html

from pywikibot_utils import safe_put

# FIXME: try to avoid hard-coding this, pywikipedia know them but often
# pywikipedia code lag a bit behind new namespace creation, get it directly
# from the database (is it possible?) or through the api (but does all
# wikisource have a correct alias for the Page: namespace?)
page_prefixes = {
    'br' : 'Pajenn',
    'ca' : 'P\xc3\xa0gina',
    'de' : 'Seite',
    'en' : 'Page',
    'es' : 'P\xc3\xa1gina',
    'et' : 'Lehek\xc3\xbclg',
    'fr' : 'Page',
    'hr' : 'Stranica',
    'hu' : 'Oldal',
    'hy' : '\xd4\xb7\xd5\xbb',
    'it' : 'Pagina',
    'la' : 'Pagina',
    'no' : 'Side',
    'old': 'Page',
    'pl' : 'Strona',
    'pt' : 'P\xc3\xa1gina',
    'ru' : '\xd1\x81\xd1\x82\xd1\x80\xd0\xb0\xd0\xbd\xd0\xb8\xd1\x86\xd0\xb0',
    'sl' : 'Stran',
    'sv' : 'Sida',
    'vec': 'Pagina',
    'vi' : 'Trang',
    'zh' : 'Page',
    }

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
        print "Error: %d, %s" % (error, text)
    return  { 'error' : error, 'text' : text }

def do_extract(mysite, maintitle, user, codelang):
    prefix = page_prefixes.get(codelang)
    if not prefix:
        return ret_val(E_ERROR, "no prefix")

    djvuname = maintitle.replace(u' ', u'_')
    print djvuname.encode('utf-8')

    # FIXME: it'll better to avoid reloading the cache at each run
    cache = lifo_cache.LifoCache('extract_text_layer')

    text_layer = align.get_djvu(cache, mysite, djvuname, True)
    if not text_layer:
        return ret_val(E_ERROR, "unable to retrieve text layer")

    text = u''
    for pos, page_text in enumerate(text_layer):
        text += u'==[[' + prefix + u':' + maintitle + u'/' + unicode(pos+1) + u']]==\n'
        text += page_text + u'\n'

    page = pywikibot.Page(mysite, u'User:' + user + u'/Text')
    safe_put(page, text, comment = u'extract text')

    return ret_val(E_OK, "")


extract_queue = []

def html_for_queue(queue):
    html = u''
    for i in queue:
        mtitle = i[0]
        codelang = i[1]
        try:
            # FIXME: do not harcode the family
            msite = pywikibot.getSite(codelang, 'wikisource')
            # FIXME: do not hardcide the namespace here.
            page = pywikibot.Page(msite, u'Livre:' + mtitle)
            path = msite.nice_get_address(page.title(asUrl = True))
            url = '%s://%s%s' % (msite.protocol(), msite.hostname(), path)
        except:
            url = ""
        html += date_s(i[3])+' '+i[2]+" "+i[1]+" <a href=\""+url+"\">"+i[0]+"</a><br/>"
    return html

# title user lang t request
def do_status(lock, queue):
    lock.acquire()
    queue = copy.copy(queue)
    lock.release()

    html = common_html.get_head('Extract text layer')
    html += u"<body><div>The robot is running.<br/><hr/>"
    html += u"<br/>%d jobs in extract queue.<br/>" % len(queue)
    html += html_for_queue(queue)
    html += u'</div></body></html>'
    return html

def bot_listening(lock):

    print date_s(time.time())+ " START"

    try:
        while True:
            request = simple_redis_ipc.wait_for_request('extract_text_layer_daemon')
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
                # FIXME: don't raise but return an error with the request a
                # error msg ?
                print "error", request
                raise

            t = time.time()
            user = user.replace(' ', '_')

            print (date_s(t) + " REQUEST " + user + ' ' + lang + ' ' + cmd + ' ' + title).encode('utf-8')

            if cmd == "extract":
                add_job(lock, extract_queue, (title, lang, user, t, request))
            elif cmd == 'status':
                html = do_status(lock, extract_queue)
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
        thread.start_new_thread(job_thread, (lock, extract_queue, do_extract))
        bot_listening(lock)
    except KeyboardInterrupt:
        pywikibot.stopme()
        os._exit(1)
    finally:
        pywikibot.stopme()
