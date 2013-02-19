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
# copyright thomasv1 at gmx dot de
# copyright phe at nowhere


# todo : use urllib


__module_name__ = "wikisourceocr"
__module_version__ = "1.0"
__module_description__ = "wikisource ocr bot"



import os
import socket
import thread
import time
import json
import hashlib
import multiprocessing
import re
import common_html
import ocr
import utils

task_queue = []

tesseract_languages = { 
	'fr':"fra",
        'en':"eng",
        'de':"deu",
        'de-f':"deu-frak",
        'la':"ita",
        'is':'isl', # needs tess 3.02
        'it':"ita",
	'es':"spa",
	'pt':"spa",
        'ru':"rus",
        }

class Request:
    def __init__(self, data, conn):
        self.url, self.lang, self.user = data.split('|')
        self.user = self.user.replace(' ','_')
        self.start_time = time.time()
        self.filename = self.url.split('/')[-1]
        self.conn = conn
        self.running = False

    def as_str(self):
        ret = date_s(self.start_time)+" REQUEST "+self.user+' '+self.lang+' '+self.filename+' '
        if self.running:
            ret += 'running'
        else:
            ret += 'waiting'
        return ret

    def key(self):
        m = hashlib.md5()
        m.update(self.lang + self.url)
        return m.hexdigest()

    def cached_name(self):
        return '/home/phe/wsbot/cache/tesseract/' + self.key()

    def cache_entry_exist(self):
        return os.path.exists(self.cached_name())

def bot_listening():

    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    try:
        sock.bind(('',12347))
    except:
        print "could not start listener : socket already in use"
        thread.interrupt_main()
        return

    print date_s(time.time())+ " START"
    sock.listen(1)

    # The other side needs to know the server name where the daemon run to open
    # the connection. We write it after bind() because we want to ensure than
    # only one instance of the daemon is running. FIXME: this is not sufficient
    # if the job is migrated so migration is disabled for this daemon.
    servername_filename = os.getenv('HOME') + '/public_html/ocr_server.server'
    if os.path.exists(servername_filename):
        os.chmod(servername_filename, 0644)
    fd = open(servername_filename, "w")
    fd.write(socket.gethostname())
    fd.close()
    os.chmod(servername_filename, 0444)

    # wait for requests
    try:
        while True:
            conn, addr = sock.accept()
            data = conn.recv(1024)
            try:
	        request = Request(data, conn)
	    except:
		print "error", data
		conn.close()
		continue

	    print request.as_str()
	    task_queue.append(request)

    finally:
	sock.close()


def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])

def ret_val(error, text):
    if error:
        print "Error: %d, %s" % (error, text)
    return  {'error' : error, 'text' : text }


def ocr_image(url, codelang, thread_id):

    lang = tesseract_languages.get(codelang, 'eng')

    basename = 'tmp/tesseract/image_%d' % thread_id

    os.system("rm -f %s.*" % basename)

    f = basename + ".jpg"

    # for debugging purpose only
    url = url.replace('http://upload.wikimedia.zaniah.virgus/',
                      'http://upload.wikimedia.org/')

    #url = url.replace("1024px","2900px")
    cmdline = "wget --no-check-certificate -q -O %s \"%s\"" % (f,url)
    print cmdline
    os.system(cmdline)
    if not os.path.exists(f):
        return ret_val(1, "could not download url: %s" % url)

    # FIXME: do we really need this conversion ?
    os.system("convert %s.jpg -compress none %s.tif" % (basename, basename))

    txt = ocr.ocr(basename + '.tif', basename, lang)
    if txt == None:
        return ret_val(2, "ocr failed")

    return ret_val(0, txt)

def do_one_file(job_queue, done_queue, thread_id):
    while True:
        url, codelang, key = job_queue.get()
        if url == None:
            print "Stopping thread"
            return
        print "start threaded job"
        # done this way to get a more accurate status, we want to know
        # which process are running and waiting so we signal the status change
        # to the parent process.
        done_queue.put( (None, key, True) )
        data = ocr_image(url, codelang, thread_id)
        done_queue.put( (data, key, False) )
        print "stop threaded job"

def next_pagename(match):
    return '%s/page%d-%spx-%s' % (match.group(1), int(match.group(2)) + 1, match.group(3), match.group(4))

class JobManager:
    def __init__(self):
        self.job_queue = None
        self.done_queue = None
        self.dict_query = {}
        self.dict_hash = {}
        self.key = 1L
        self.start_subprocess()

    def start_subprocess(self):
        num_worker_threads = 2
        thread_array = []
        self.job_queue = multiprocessing.Queue(num_worker_threads * 16)
        self.done_queue = multiprocessing.Queue()
        args = (self.job_queue, self.done_queue)
        for i in range(num_worker_threads):
            print "starting thread"
            t = multiprocessing.Process(target=do_one_file, args=args + (i, ))
            t.daemon = True
            t.start()
            thread_array.append(t)

    def finish_job(self, done_key, data):
        print "pop job: job finished"
        err = data['error']
        data = json.dumps(data)
        r = self.dict_query[done_key]

        # null conn is possible if this is a prefetched job
        if r.conn:
            r.conn.send(data)
            r.conn.close()

        # error are already logged by the subprocess
        if not err:
            utils.save_obj(r.cached_name(), data)

        time2 = time.time()
        print date_s(time2)+r.user+" "+r.lang+" %s (%.2f)"%(r.filename, time2-r.start_time)
        if self.dict_query[done_key].key() in self.dict_hash:
            del self.dict_hash[self.dict_query[done_key].key()]
        del self.dict_query[done_key]

    def flush_done_job(self):
        while not self.done_queue.empty():
            data, done_key, running = self.done_queue.get()
            if running:
                print "pop job: status change"
                self.dict_query[done_key].running = True
            else:
                self.finish_job(done_key, data)

    def new_request(self, request):
        if request.cache_entry_exist():
            print "cache success"
            data = utils.load_obj(request.cached_name())
            if request.conn:
                request.conn.send(data)
                request.conn.close()
            time2 = time.time()
            print date_s(time2)+request.user+" "+request.lang+" %s (%.2f)"%(request.filename, time2-request.start_time)
        else:
            if request.key() in self.dict_hash and self.dict_hash[request.key()].user == request.user:
                print "reusing a waiting job"
                old_conn = self.dict_hash[request.key()].conn
                if old_conn:
                    old_conn.close()
                self.dict_hash[request.key()].conn = request.conn
            else:
                print "push job"
                self.push_job(request)
        next_page = re.sub('^(.*)/page(\d+)-(\d+)px-(.*)$', next_pagename, request.url)
        if next_page:
            prefetch_request = Request('|'.join([next_page, request.lang, request.user]), None)
            if not prefetch_request.cache_entry_exist():
                print "push prefetched job: ", prefetch_request.filename
                self.push_job(prefetch_request)

    def push_job(self, request):
        self.dict_query[self.key] = request
        self.dict_hash[request.key()] = request
        self.job_queue.put( (request.url, request.lang, self.key) )
        self.key += 1

    def status(self, request):
        html = common_html.get_head('OCR service')
        html += '<body><div>The robot is runnning.<br /><hr />'
        html += date_s(request.start_time) + " STATUS: "
        html += "%d jobs in queue.<br/>" % len(self.dict_query)
        for val in self.dict_query.itervalues():
            html += val.as_str() + '<br />'
        html += '</div></body></html>'

        request.conn.send(html)
        request.conn.close()

    def handle_request(self, request):
        if request.url == 'status':
            self.status(request)
        else:
            self.new_request(request)

def main():
    thread.start_new_thread(bot_listening,())

    job_manager = JobManager()

    while True:
        if len(task_queue):
            job_manager.handle_request(task_queue.pop(0))
        else:
            time.sleep(0.5)

            job_manager.flush_done_job()

if __name__ == "__main__":
    main()
