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
# TODO:
#
#   Allow to cancel job, bot through the web api and
# when a job superseed a running or queued job because the File:
# is out of date.
#
#   Web api and internal queue should use a dict not a tuple.
#
#
#    copyright phe @ nowhere

__module_name__ = "wshocr"
__module_version__ = "1.0"
__module_description__ = "wikisource hocr server"

import errno
import os
import socket
import re
import thread
import time
import copy
import json
import common_html
import hashlib
import utils
import signal
import sys
import utils
import traceback
sys.path.append("/home/phe/pywikipedia")
import wikipedia
import align
sys.path.append("/home/phe/tools")
import djvu_text_to_hocr
import task_scheduler
import ocr_djvu
import ocr
import urllib

mylock = thread.allocate_lock()

task_s = task_scheduler.TaskScheduler(silent = True)

E_ERROR = 1
E_OK = 0

jobs = None

class Request:
    def __init__(self, dct, conn):
        self.cmd = dct['cmd']
        self.conn = conn
        self.start_time = time.time()
        if self.cmd != 'status':
            self.page = dct['page']
            if '%' in self.page:
                self.page = urllib.unquote_plus(self.page)
            self.user = dct['user']
            # compat, FIXME, needed ?
            self.user = self.user.replace(' ', '_')
            self.lang = dct['lang']
            self.book_name = re.sub('^(.*)/[0-9]+$', '\\1', self.page)
            # compat, FIXME; needed ?
            self.book_name = self.book_name.replace('_', ' ')
            # cached path cache, not reliable, used to get the path for
            # do_get() request only, don't use it for other purpose.
            # FIXME: this is obfuscation.
            self.cache_path = cache_path(self.book_name, self.lang, 'wikisource')
        else:
            self.page = ''
            self.user = ''
            self.book_name = ''
            self.cache_path = ''
            self.lang = ''

    def print_request_start(self):
        print date_s(self.start_time), "REQUEST", self.user, self.lang, self.cmd, self.page

    def print_request_end(self):
        time2 = time.time()
        print date_s(time2), self.user, self.lang, self.page, self.cmd, " (%.2f)" % (time2-self.start_time)

    def to_html(self):
        return date_s(self.start_time) + ' ' + self.user + ' ' + self.lang + ' ' + self.page + '<br/>'


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
            request = queue[-1]
            got_it = True
        lock.release()

    return request

def remove_job(lock, queue):
    lock.acquire()
    queue.pop()
    lock.release()

def add_job(lock, queue, cmd):
    lock.acquire()
    queue.insert(0, cmd)
    lock.release()

def cache_path(book_name, lang, family):
    base_dir  = '/mnt/user-store/phe/cache/hocr/%s/%s/' % (family, lang)
    base_dir += '%s/%s/%s/%s/'

    h = hashlib.md5()
    h.update(book_name)
    h = h.hexdigest()

    base_dir = base_dir % (h[0:2], h[2:4], h[4:6], h[6:])

    if not os.path.exists(base_dir) and family != 'commons':
        return cache_path(book_name, 'commons', 'commons')

    return base_dir

def ret_val(error, text, log = True):
    if log:
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

def check_and_upload(url, filename, sha1):
    if not os.path.exists(filename) or utils.sha1(filename) != sha1:
        # file deleted by the job queue processing this item.
        align.copy_file_from_url(url, filename)
    else:
        ret_val(E_ERROR, "book already uploaded: " + filename)

# check if data are uptodate
#
# return -1 if the File: no longer exists
# -2 an exception occur, likely to be a network error raised
# by pywikipedia
# 0 data exist but aren't uptodate
# 1 data exist and are uptodate
# if it return 0 the file is uploaded if it's not already exists
def is_uptodate(request):
    try:
        site = wikipedia.getSite(code = request.lang, fam = 'wikisource')
        filepage = align.get_filepage(site, unicode(request.book_name, 'utf-8'))
        if filepage == None or not filepage.exists():
            # file deleted between the initial request and now 
            return -1
    except Exception, e:
        exc_type, exc_value, exc_tb = sys.exc_info()
        try:
            print >> sys.stderr, 'TRACEBACK'
            print >> sys.stderr, request.book_name
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            del exc_tb
        return -2

    # We can't use the cached path cache in the request but we update it here.
    request.cache_path = cache_path(request.book_name, filepage.site().lang, filepage.site().fam().name)

    sha1 = filepage.getHash()
    if check_sha1(request.cache_path, sha1):
        return 1

    if not os.path.exists(request.cache_path):
        os.makedirs(path)
    check_and_upload(filepage.fileUrl(), request.cache_path + request.book_name, sha1)
    return 0

def do_hocr_djvu(request):
    options = djvu_text_to_hocr.default_options()
    options.compress = 'bzip2'
    options.out_dir = request.cache_path
    options.silent = True

    filename = request.cache_path + request.book_name

    # Needed if the same job was queued twice before the first run terminate.
    uptodate = is_uptodate(request)
    if uptodate < 0:
        return ret_val(E_ERROR, "do_hocr_djvu(): book not found (file deleted since initial request ?) or exception: " + filename)
    elif uptodate == 1:
        return ret_val(E_OK, "do_hocr_djvu(): book already hocred: " + filename)

    if djvu_text_to_hocr.parse(options, filename) == 0:
        sha1 = utils.sha1(filename)
        utils.write_sha1(sha1, options.out_dir + "sha1.sum")
        os.remove(filename)
        return ret_val(E_OK, "do_hocr_djvu() success: " + filename)
    else:
        request.start_time = time.time()
        jobs['number_of_hocr_tesseract_job'] += 1
        add_job(lock, jobs['hocr_tesseract_queue'], request)
        return ret_val(E_ERROR, "do_hocr_djvu() failure, moving to slow queue: " + filename)

# Don't try to move the job to the fast queue, even if it look like
# possible, else if the fast queue fail the job will be queued in this
# (slow) queue and it'll ping-pong between the queues forever.
def do_hocr_tesseract(request):

    filename = request.cache_path + request.book_name

    options = ocr_djvu.default_options()

    options.silent = True
    options.compress = 'bzip2'
    options.config = 'hocr'
    options.num_thread = -1
    options.lang = ocr.tesseract_languages.get(request.lang, 'eng')

    options.out_dir = request.cache_path

    # Needed if the same job was queued twice before the first run terminate.
    uptodate = is_uptodate(request)
    if uptodate < 0:
        return ret_val(E_ERROR, "do_hocr_tesseract(): book not found (file deleted since initial request ?) or exception: " + filename)
    elif uptodate == 1:
        return ret_val(E_ERROR, "do_hocr_tesseract(): book already hocred: " + filename)

    global task_s

    if ocr_djvu.ocr_djvu(options, filename, task_s) == 0:
        sha1 = utils.sha1(filename)
        utils.write_sha1(sha1, options.out_dir + "sha1.sum")
        os.remove(filename)
    else:
        return ret_val(E_ERROR, "do_hocr_tesseract() unable to process: " + filename)

    return ret_val(E_OK, "do_hocr_tesseract() finished: " + filename)

def do_hocr(request):
    uptodate = is_uptodate(request)
    if uptodate < 0:
        return ret_val(E_ERROR, "do_hocr(): book not found (file deleted since initial request ?) or exception: " + request.book_name)
    elif uptodate == 1:
        return ret_val(E_ERROR, "do_hocr(): book already hocred: " + request.book_name)

    request = copy.copy(request)
    request.start_time = time.time()
    request.conn = None

    if djvu_text_to_hocr.has_word_bbox(request.cache_path + request.book_name):
        jobs['number_of_hocr_djvu_job'] += 1
        add_job(lock, jobs['hocr_djvu_queue'], request)
        queue_type = "fast"
    else:
        jobs['number_of_hocr_tesseract_job'] += 1
        add_job(lock, jobs['hocr_tesseract_queue'], request)
        queue_type = "slow"

    return ret_val(E_OK, "job queued and waiting processing in the %s queue: %s path %s" % (queue_type, request.page, request.cache_path))

def do_get(request):
    page_nr = re.sub('^.*/([0-9]+)$', '\\1', request.page)
    try:
        page_nr = int(page_nr)
    except:
        return ret_val(E_ERROR, "unable to extract page number from page: " + request.page)

    filename = request.cache_path + 'page_%04d.html' % page_nr

    # We support data built with different compress scheme than the one
    # actually generated by the server
    text = utils.uncompress_file(filename, [ 'bzip2', 'gzip', '' ])
    if text == None:
        return ret_val(E_ERROR, "unable to locate file %s for page %s" % (filename, request.page))

    return ret_val(E_OK, text, False)

def html_for_queue(queue):
    html = ''
    for request in queue:
        html += request.to_html()
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
    for request in queue:
        if request.conn:
            request.close()
            request.conn = None

# either called through a SIGUSR2 or a finally clause.
# FIXME: unsafe, see comment when the signal handler is installed.
def on_exit(sign_nr, frame):
        print "STOP"

        task_s.reset_all_group()

        # no value to save the get queue but we must close conn.
        stop_queue(jobs['get_queue'])
        jobs['get_queue'] = []

        stop_queue(jobs['hocr_queue'])
        stop_queue(jobs['hocr_djvu_queue'])
        stop_queue(jobs['hocr_tesseract_queue'])

        utils.save_obj("/home/phe/wshocr.jobs", jobs)

def utf8_encode_dict(data):
    ascii_encode = lambda x: x.encode('utf-8')
    return dict(map(ascii_encode, pair) for pair in data.items())

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
            try:
                conn, addr = sock.accept()
                data = conn.recv(1024)
            except socket.error as s_err:
                if s_err.errno != errno.EINTR:
                    raise ose
                continue

            try:
                json_data = json.loads(data, object_hook=utf8_encode_dict)
                request = Request(json_data, conn)
            except:
                # FIXME: must return valid data to the connection.
                print "FATAL: Ill formed request", data
                conn.close()
                continue

            request.print_request_start()

            if request.cmd == "status":
                do_status(lock, conn)
            elif request.cmd == 'hocr':
                jobs['number_of_hocr_job'] += 1
                add_job(lock, jobs['hocr_queue'], request)
            elif request.cmd == "get":
                jobs['number_of_get_job'] += 1
                add_job(lock, jobs['get_queue'], request)
            else:
                out = ret_val(E_ERROR, "unknown command: " + request.cmd)
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
        request = get_job(lock, queue)

        # FIXME: too verbose ?
        print request.page, request.user, request.lang

        out = func(request)

        if request.conn:
            print "Closing conn", os.getpid()
            request.conn.sendall(json.dumps(out))
            request.conn.close()

        request.print_request_end()

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
    # FIXME: all thread will inherit that and for thread started with Thread
    # they'll inherit the signal handler even for those started before
    # the signal handler is installed. FIXME: this is not true, there is
    # another problem elsewhere
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
