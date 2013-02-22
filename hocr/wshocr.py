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
import utils
import signal
import sys
sys.path.append("/home/phe/pywikipedia")
import wikipedia
import align
sys.path.append("/home/phe/tools")
import djvu_text_to_hocr
import ocr_djvu
# FIXME: lang to tidy, should be in ocr.py
import ocrdaemon

mylock = thread.allocate_lock()

E_ERROR = 1
E_OK = 0

jobs = None

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

def cache_path(book_name, lang, family):

    book_name = book_name.replace('_', ' ')

    base_dir  = '/mnt/user-store/phe/cache/hocr/%s/%s/' % (family, lang)
    base_dir += '%s/%s/%s/%s/'

    h = hashlib.md5()
    h.update(book_name)
    h = h.hexdigest()

    base_dir = base_dir % (h[0:2], h[2:4], h[4:6], h[6:])

    if not os.path.exists(base_dir) and family != 'commons':
        return cache_path(book_name, 'commons', 'commons')

    return base_dir

def ret_val(error, text):
    if error:
        print "Error: %d, %s" % (error, text)
    return  { 'error' : error, 'text' : text }

def check_sha1(path, sha1):
    if os.path.exists(path + "sha1.sum"):
        fd = open(path + "sha1.sum")
        old_sha1 = fd.read()
        fd.close()
        if old_sha1 == sha1:
            return True
    return False

# check if data are uptodate
# return -1 if the File: no longer exists
# 0 data exist but aren't uptodate
# 1 data exist and are uptodate
def is_uptodate(path, filename, codelang):
    site = wikipedia.getSite(code = codelang, fam = 'wikisource')
    filepage = align.get_filepage(site, unicode(filename, 'utf-8'))
    if filepage == None or not filepage.exists():
        # file deleted between the initial request and now 
        return -1

    sha1 = filepage.getHash()
    if check_sha1(path + '/', sha1):
        return 1
    return 0

def do_hocr_djvu(filename, user, codelang):
    options = djvu_text_to_hocr.default_options()
    options.gzip = True
    path = os.path.split(filename)
    options.out_dir = path[0] + '/'
    options.silent = True

    # redo the sha1 check, this is needed if the same job was queued
    # twice before the first run terminate.
    uptodate = is_uptodate(path[0], path[1], codelang)
    if uptodate == -1:
        return ret_val(E_ERROR, "do_hocr_djvu(): book not found (file deleted since initial request ?)")
    elif uptodate == 1:
        return ret_val(E_ERROR, "do_hocr_djvu(): book already hocred")

    if djvu_text_to_hocr.parse(options, filename):
        sha1 = ocr_djvu.sha1(filename)
        ocr_djvu.write_sha1(sha1, options.out_dir + "sha1.sum")
        os.remove(filename)
        return ret_val(E_OK, "do_hocr_djvu() success")
    else:
        return ret_val(E_ERROR, "do_hocr_djvu() failure")

def do_hocr_tesseract(filename, user, codelang):
    options = ocr_djvu.default_options()

    options.silent = False
    options.gzip = True
    options.config = 'hocr'
    # FIXME ?
    options.num_thread = 2
    options.lang = ocrdaemon.tesseract_languages.get(codelang, 'eng')

    # FIXME: changing dir is really a bad idea, see below all restore of cwd
    # and chdir has global side effect, so it can break other thread...
    # we need an options.out_dir to ocr_djvu.py
    path = os.path.split(filename)
    old_cwd = os.getcwd()
    os.chdir(path[0])

    # redo the sha1 check, this is needed if the same job was queued
    # twice before the first run terminate.
    uptodate = is_uptodate(path[0], path[1], codelang)
    if uptodate == -1:
        os.chdir(old_cwd)
        return ret_val(E_ERROR, "do_hocr_tesseract(): book not found (file deleted since initial request ?)")
    elif uptodate == 1:
        os.chdir(old_cwd)
        return ret_val(E_ERROR, "dp_hocr_tessseract(): book already hocred")

    if ocr_djvu.ocr_djvu(options, path[1]):
        sha1 = ocr_djvu.sha1(filename)
        ocr_djvu.write_sha1(sha1)
        os.remove(filename)

    os.chdir(old_cwd)

    return ret_val(E_OK, "do_hocr_tesseract() finished")

def do_hocr(page, user, codelang):
    book_name = re.sub('^(.*)/[0-9]+$', '\\1', page)

    site = wikipedia.getSite(code = codelang, fam = 'wikisource')
    filepage = align.get_filepage(site, unicode(book_name, 'utf-8'))
    if filepage == None or not filepage.exists():
        return ret_val(E_ERROR, "wiki page not found")

    path = cache_path(book_name, filepage.site().lang, filepage.site().fam().name)
    sha1 = filepage.getHash()
    if check_sha1(path, sha1):
        return ret_val(E_OK, "book already hocred")

    if not os.path.exists(path):
        os.makedirs(path)

    if not os.path.exists(path + book_name) or ocr_djvu.sha1(path + book_name) != sha1:
        # file deleted by the job queue processing this item.
        align.copy_file_from_url(filepage.fileUrl(), path + book_name)
    else:
        ret_val(E_ERROR, "book already uploaded")

    t = time.time()

    if djvu_text_to_hocr.has_word_bbox(path + book_name):
        jobs['number_of_hocr_djvu_job'] += 1
        add_job(lock, jobs['hocr_djvu_queue'], (path + book_name, codelang, user, t, None))
        queue_type = "fast"
    else:
        jobs['number_of_hocr_tesseract_job'] += 1
        add_job(lock, jobs['hocr_tesseract_queue'], (path + book_name, codelang, user, t, None))
        queue_type = "slow"

    return ret_val(E_OK, "job queued and waiting processing in the %s queue" % queue_type)

def do_get(page, user, codelang):
    page_nr = re.sub('^.*/([0-9]+)$', '\\1', page)
    try:
        page_nr = int(page_nr)
    except:
        return ret_val(E_ERROR, "unable to extract page number from page=")

    book_name = re.sub('^(.*)/[0-9]+$', '\\1', page)

    base_dir = cache_path(book_name, codelang, 'wikisource')

    filename = base_dir + 'page_%04d.html' % page_nr

    if os.path.exists(filename + '.gz'):
        fd = gzip.open(filename + '.gz')
    elif os.path.exists(filename):
        fd = open(filename)
    else:
        return ret_val(E_ERROR, "unable to locate file %s for page %s" % (filename, page))

    text = fd.read()
    fd.close()

    return ret_val(E_OK, text)

def html_for_queue(queue):
    html = ''
    for i in queue:
        html += date_s(i[3])+' '+i[2]+" "+i[1]+" "+i[0]+"<br/>"
    return html

def do_status(lock, conn):
    lock.acquire()
    get_queue = copy.deepcopy(jobs['get_queue'])
    hocr_queue = copy.deepcopy(jobs['hocr_queue'])
    hocr_djvu_queue = copy.deepcopy(jobs['hocr_djvu_queue'])
    hocr_tesseract_queue = copy.deepcopy(jobs['hocr_tesseract_queue'])
    lock.release()

    html = common_html.get_head('hOCR server status')

    html += "<body><div>the robot is running.<br/><hr/>"
    html += "<br/>%d get request queued.<br/>" % len(get_queue)
    html += html_for_queue(get_queue)
    html += "<br/>%d hocr request queued.<br/>" % len(hocr_queue)
    html += html_for_queue(hocr_queue)
    html += "<br/>%d hocr djvu queued.<br/>" % len(hocr_djvu_queue)
    html += html_for_queue(hocr_djvu_queue)
    html += "<br/>%d hocr tesseract queued.<br/>" % len(hocr_tesseract_queue)
    html += html_for_queue(hocr_tesseract_queue)
    html += "<br/>%(number_of_get_job)d get since server start<br/>" % jobs
    html += "<br/>%(number_of_hocr_job)d hocr since server start<br/>" % jobs
    html += "<br/>%(number_of_hocr_djvu_job)d djvu hocr since server start<br/>" % jobs
    html += "<br/>%(number_of_hocr_tesseract_job)d tesseract hocr since server start<br/>" % jobs
    html += '</div></body></html>'

    conn.sendall(html)
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

        # no value to save the get queue but we must close conn.
        stop_queue(jobs['get_queue'])
        jobs['get_queue'] = []

        stop_queue(jobs['hocr_queue'])
        stop_queue(jobs['hocr_djvu_queue'])
        stop_queue(jobs['hocr_tesseract_queue'])

        utils.save_obj("/home/phe/wshocr.jobs", jobs)

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
            elif cmd == 'hocr':
                jobs['number_of_hocr_job'] += 1
                add_job(lock, jobs['hocr_queue'], (page, lang, user, t, conn))
            elif cmd == "get":
                jobs['number_of_get_job'] += 1
                add_job(lock, jobs['get_queue'], (page, lang, user, t, conn))
            else:
                out = ret_val(E_ERROR, "unknown command: " + cmd)
                conn.sendall(json.dumps(out));
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
        out = func(page, user, codelang)

        if conn:
            conn.sendall(json.dumps(out))
            conn.close()

        time2 = time.time()
        print date_s(time2), page, user, codelang, " (%.2f)" % (time2-time1)

        remove_job(lock, queue)

def default_jobs():
    return {
        'get_queue' : [],
        'number_of_get_job' : 0,
        'hocr_queue' : [],
        'number_of_hocr_job' : 0,
        'hocr_djvu_queue' : [],
        'number_of_hocr_djvu_job' : 0,
        'hocr_tesseract_queue' : [],
        'number_of_hocr_tesseract_job' : 0,
        }

if __name__ == "__main__":
    # qdel send a SIGUSR2 if -notify is used when starting the job.
    signal.signal(signal.SIGUSR2, on_exit)
    try:
        jobs = utils.load_obj("/home/phe/wshocr.jobs")
    except:
        jobs = default_jobs()

    # Backward compatibility
    for key, value in default_jobs().iteritems():
        jobs.setdefault(key, value)

    lock = thread.allocate_lock()
    thread.start_new_thread(job_thread, (lock, jobs['get_queue'], do_get))
    thread.start_new_thread(job_thread, (lock, jobs['hocr_queue'], do_hocr))
    thread.start_new_thread(job_thread, (lock, jobs['hocr_djvu_queue'], do_hocr_djvu))
    thread.start_new_thread(job_thread, (lock, jobs['hocr_tesseract_queue'], do_hocr_tesseract))
    bot_listening(lock)
