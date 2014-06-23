# -*- coding: utf-8 -*-
# GPL V2, author phe

__module_name__ = "wshocr"
__module_version__ = "1.0"
__module_description__ = "wikisource hocr server"

import tool_connect
import os
import re
import thread
import time
import copy
import common_html
import hashlib
import utils
import signal
import sys
import traceback
import pywikibot
import align
import djvu_text_to_hocr
#import task_scheduler
import ocr_djvu
import ocr
import job_queue

#task_s = task_scheduler.TaskScheduler(silent = True)

E_ERROR = 1
E_OK = 0

jobs = None

class Request:
    def __init__(self, dct, conn, tools):
        print dct
        self.cmd = dct['cmd']
        self.conn = conn
        self.tools = tools
        self.start_time = time.time()
        if not self.cmd in [ 'status', 'ping' ]:
            self.page = dct['page']
            self.user = dct['user']
            self.lang = dct['lang']
            self.book_name = re.sub(u'^(.*?)(/[0-9]+)?$', u'\\1', self.page)
            self.book_name = self.book_name.replace(u'_', u' ')
        else:
            self.page = ''
            self.user = ''
            self.book_name = ''
            self.lang = ''

    def print_request_start(self):
        print (date_s(self.start_time) + u" REQUEST " + self.user + u' ' + self.lang + u' ' + self.cmd + u' ' + self.page).encode('utf-8')

    def print_request_end(self):
        time2 = time.time()
        print (date_s(time2) + u' ' + self.user + u' ' + self.lang + u' ' + self.page + u' '+ self.cmd + " (%.2f)" % (time2-self.start_time)).encode('utf-8')

    def to_html(self):
        return date_s(self.start_time) + ' ' + self.user + ' ' + self.lang + ' ' + self.book_name + '<br/>'


def cache_path(book_name):
    if type(book_name) == type(u''):
        book_name = book_name.encode('utf-8')

    base_dir  = os.path.expanduser('~/cache/hocr/') + '%s/%s/%s/%s/'

    h = hashlib.md5()
    h.update(book_name)
    h = h.hexdigest()

    return base_dir % (h[0:2], h[2:4], h[4:6], h[6:])

def ret_val(error, text):
    if error:
        print "Error: %d, %s" % (error, text.encode('utf-8'))
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
    real_filename = filename.encode('utf-8')
    if not os.path.exists(real_filename) or utils.sha1(real_filename) != sha1:
        # file deleted by the job queue processing this item.
        if not utils.copy_file_from_url(url, real_filename):
            return False
    else:
        ret_val(E_ERROR, "book already uploaded: " + filename)

    return True

# check if data are uptodate
#
# return:
# -1 if the File: no longer exists
# -2 an exception occur, likely to be a network error raised by pywikibot
# -3 and exception occured during file copy 
#  0 data exist but aren't uptodate
#  1 data exist and are uptodate
# if it return 0 the file is uploaded if it not already exists
def is_uptodate(request):
    path = cache_path(request.book_name)

    try:
        site = pywikibot.getSite(code = request.lang, fam = 'wikisource')
        filepage = align.get_filepage(site, request.book_name)
        if not filepage:
            # file deleted between the initial request and now 
            return -1
        sha1 = filepage.getFileSHA1Sum()
    except Exception, e:
        exc_type, exc_value, exc_tb = sys.exc_info()
        try:
            print >> sys.stderr, 'TRACEBACK'
            print >> sys.stderr, request.book_name.encode('utf-8')
            traceback.print_exception(exc_type, exc_value, exc_tb)
        finally:
            del exc_tb
        return -2

    if check_sha1(path, sha1):
        return 1

    if not os.path.exists(path):
        os.makedirs(path)
    if not check_and_upload(filepage.fileUrl(), os.path.expanduser('~/tmp/') + request.book_name, sha1):
        return -3
    return 0

def do_hocr_djvu(request):
    path = cache_path(request.book_name)
    options = djvu_text_to_hocr.default_options()
    options.compress = 'bzip2'
    options.out_dir = path
    options.silent = True

    filename = os.path.expanduser('~/tmp/') + request.book_name

    # Needed if the same job was queued twice before the first run terminate.
    uptodate = is_uptodate(request)
    if uptodate < 0:
        return ret_val(E_ERROR, "do_hocr_djvu(): book not found (file deleted since initial request ?) or exception: " + filename)
    elif uptodate == 1:
        return ret_val(E_OK, "do_hocr_djvu(): book already hocred: " + filename)

    request.start_time = time.time()

    if djvu_text_to_hocr.parse(options, filename) == 0:
        sha1 = utils.sha1(filename)
        utils.write_sha1(sha1, options.out_dir + "sha1.sum")
        os.remove(filename)
        return ret_val(E_OK, "do_hocr_djvu() success: " + filename)
    else:
        request.start_time = time.time()
        jobs['number_of_hocr_tesseract_job'] += 1
        jobs['hocr_tesseract_queue'].put(request)
        return ret_val(E_ERROR, "do_hocr_djvu() failure, moving to slow queue: " + filename)

# Don't try to move the job to the fast queue, even if it look like
# possible, else if the fast queue fail the job will be queued in this
# (slow) queue and it'll ping-pong between the queues forever.
def do_hocr_tesseract(request):

    request.start_time = time.time()

    path = cache_path(request.book_name)
    filename = os.path.expanduser('~/tmp/') + request.book_name

    # FIXME: inhibited atm
    if os.path.exists(filename):
        os.remove(filename)
    return

    options = ocr_djvu.default_options()

    options.silent = True
    options.compress = 'bzip2'
    options.config = 'hocr'
    options.num_thread = -1
    options.lang = ocr.tesseract_languages.get(request.lang, 'eng')

    options.out_dir = path

    t1 = time.time()

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

    print "elapsed: %.2f" % (time.time() - t1)

    return ret_val(E_OK, "do_hocr_tesseract() finished: " + filename)

def do_hocr(request):
    uptodate = is_uptodate(request)
    if uptodate < 0:
        return ret_val(E_ERROR, "do_hocr(): book not found (file deleted since initial request ?) or exception: " + request.book_name)
    elif uptodate == 1:
        return ret_val(E_ERROR, "do_hocr(): book already hocred: " + request.book_name)

    request = copy.copy(request)
    request.conn = None
    request.tools = None

    path = cache_path(request.book_name)

    if djvu_text_to_hocr.has_word_bbox(os.path.expanduser('~/tmp/') + request.book_name):
        jobs['number_of_hocr_djvu_job'] += 1
        jobs['hocr_djvu_queue'].put(request)
        queue_type = "fast"
    else:
        jobs['number_of_hocr_tesseract_job'] += 1
        jobs['hocr_tesseract_queue'].put(request)
        queue_type = "slow"

    return ret_val(E_OK, u"job queued and waiting processing in the %s queue: %s path %s" % (queue_type, request.page, path))

def do_get(request):
    page_nr = re.sub('^.*/([0-9]+)$', '\\1', request.page)
    try:
        page_nr = int(page_nr)
    except:
        return ret_val(E_ERROR, u"unable to extract page number from page: " + request.page)

    path = cache_path(request.book_name)

    filename = path + 'page_%04d.html' % page_nr

    # We support data built with different compress scheme than the one
    # actually generated by the server
    text = utils.uncompress_file(filename, [ 'bzip2', 'gzip', '' ])
    if text == None:
        return ret_val(E_ERROR, u"unable to locate file %s for page %s" % (filename, request.page))

    return ret_val(E_OK, text)

def html_for_queue(queue):
    html = u''
    for request in queue:
        html += request[0].to_html()
    return html

def do_status():
    get_queue = jobs['get_queue'].copy_items(get_last= True)
    hocr_queue = jobs['hocr_queue'].copy_items(get_last = True)
    hocr_djvu_queue = jobs['hocr_djvu_queue'].copy_items(get_last = True)
    hocr_tesseract_queue = jobs['hocr_tesseract_queue'].copy_items(get_last = True)

    html = common_html.get_head('hOCR server status')

    html += u"<body><div>the robot is running.<br/><hr/>"
    html += u"<br/>%d get request queued.<br/>" % len(get_queue)
    html += html_for_queue(get_queue)
    html += u"<br/>%d hocr request queued.<br/>" % len(hocr_queue)
    html += html_for_queue(hocr_queue)
    html += u"<br/>%d hocr djvu queued.<br/>" % len(hocr_djvu_queue)
    html += html_for_queue(hocr_djvu_queue)
    html += u"<br/>%d hocr tesseract queued.<br/>" % len(hocr_tesseract_queue)
    html += html_for_queue(hocr_tesseract_queue)
    html += u"<br/>%(number_of_get_job)d get since server start<br/>" % jobs
    html += u"<br/>%(number_of_hocr_job)d hocr since server start<br/>" % jobs
    html += u"<br/>%(number_of_hocr_djvu_job)d djvu hocr since server start<br/>" % jobs
    html += u"<br/>%(number_of_hocr_tesseract_job)d tesseract hocr since server start<br/>" % jobs
    html += u'</div></body></html>'

    return html

def stop_queue(queue):
    new_queue = job_queue.JobQueue()
    items = queue.copy_items()
    for request in items:
        if request.conn:
            request.conn.close()
        request.tools = None
        request.conn = Nonr
        new_queue.put(request)
    return new_queue

# either called through a SIGUSR2 or a finally clause.
# FIXME: unsafe, see comment when the signal handler is installed.
def on_exit(sign_nr, frame):
        print "STOP"

        #task_s.reset_all_group()

        # no value to save the get queue but we must close conn.
        stop_queue(jobs['get_queue'])
        jobs['get_queue'] = job_queue.JobQueue()

        stop_queue(jobs['hocr_queue'])
        stop_queue(jobs['hocr_djvu_queue'])
        stop_queue(jobs['hocr_tesseract_queue'])

        utils.save_obj("/home/phe/wshocr.jobs", jobs)

def bot_listening():

    tools = tool_connect.ToolConnect('hocr_daemon', 45134)

    try:
        while True:
            request, conn = tools.wait_request()
            try:
                request = Request(request, conn, tools)
            except:
                ret = ret_val(E_ERROR, u"FATAL: Ill formed request")
                print >> sys.stderr, request
                tools.send_reply(conn, ret)
                conn.close()
                continue

            request.print_request_start()

            if request.cmd == "status":
                html = do_status()
                tools.send_text_reply(conn, html)
                conn.close()
            elif request.cmd == 'hocr':
                jobs['number_of_hocr_job'] += 1
                jobs['hocr_queue'].put(request)
            elif request.cmd == "get":
                jobs['number_of_get_job'] += 1
                jobs['get_queue'].put(request)
            elif request.cmd == 'ping':
                tools.send_reply(conn, ret_val(E_OK, 'pong'))
                conn.close()
            else:
                tools.send_reply(conn, ret_val(E_ERROR, u"unknown command: " + cmd))
                conn.close()

    finally:
        tools.close()

def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])

def job_thread(queue, func):
    while True:
        request = queue.get()[0]

        out = func(request)

        if request.conn and request.tools:
            request.tools.send_reply(request.conn, out)
            request.conn.close()

        request.print_request_end()

        queue.remove()

def default_jobs():
    return {
        'get_queue' : job_queue.JobQueue(),
        'number_of_get_job' : 0,
        'hocr_queue' : job_queue.JobQueue(),
        'number_of_hocr_job' : 0,
        'hocr_djvu_queue' : job_queue.JobQueue(),
        'number_of_hocr_djvu_job' : 0,
        'hocr_tesseract_queue' : job_queue.JobQueue(),
        'number_of_hocr_tesseract_job' : 0,
        }

if __name__ == "__main__":
    # FIXME: all thread will inherit that and for thread started with Thread
    # they'll inherit the signal handler even for those started before
    # the signal handler is installed. FIXME: this is not true, there is
    # another problem elsewhere
    # qdel send a SIGUSR2 if -notify is used when starting the job.
    #signal.signal(signal.SIGUSR2, on_exit)
    try:
        jobs = utils.load_obj("/home/phe/wshocr.jobs")
    except:
        jobs = default_jobs()

    try:
        thread.start_new_thread(job_thread, (jobs['get_queue'], do_get))
        thread.start_new_thread(job_thread, (jobs['hocr_queue'], do_hocr))
        thread.start_new_thread(job_thread, (jobs['hocr_djvu_queue'], do_hocr_djvu))
        thread.start_new_thread(job_thread, (jobs['hocr_tesseract_queue'], do_hocr_tesseract))
        bot_listening()
    except KeyboardInterrupt:
        pywikibot.stopme()
        os._exit(1)
    finally:
        pywikibot.stopme()
