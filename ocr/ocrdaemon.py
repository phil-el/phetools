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
import simplejson
import multiprocessing

task_queue = []

tesseract_languages = { 
	'fr':"fra",
        'en':"eng",
        'de':"deu",
        'de-f':"deu-frak",
        'la':"ita",
        'it':"ita",
	'es':"spa",
	'pt':"spa"
        }

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
	        url,lang,user = eval(data)
	    except:
		print "error",data
		conn.close()
		continue

	    t = time.time()
	    user = user.replace(' ','_')

	    print date_s(t)+" REQUEST "+user+' '+lang+' '+url.split('/')[-1]
	    task_queue.insert(0,(url,lang,user,t,conn))

    finally:
	sock.close()


def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])

def ret_val(error, text):
    if error:
        print "Error: %d, %s" %(error, text)
    return simplejson.dumps({'error' : error, 'text' : text })


def ocr_image(url, codelang, thread_id):

    lang = tesseract_languages.get(codelang, 'eng')

    basename = 'image_%d' % thread_id

    os.system("rm -f %s.*" % basename)

    f = basename + ".jpg"

    # for debugging purpose only
    url = url.replace('http://upload.wikimedia.zaniah.virgus/',
                      'http://upload.wikimedia.org/')

    #url = url.replace("1024px","2900px")
    os.system("wget -q -O %s \"%s\""%(f,url))
    if not os.path.exists(f):
        return ret_val(1, "could not download url: %s" % url)

    os.system("convert %s.jpg -compress none %s.tif" % (basename, basename))

    os.putenv('LD_PRELOAD', '/opt/ts/lib/libtesseract_cutil.so.3')
    if lang == 'deu-frak':
        os.putenv('TESSDATA_PREFIX', '/home/phe/wsbot/')

    os.system("tesseract %s.tif %s -l %s 2>>tesseract_err"% (basename, basename, lang))

    os.unsetenv('LD_PRELOAD')
    os.unsetenv('TESSDATA_PREFIX')

    try:
        file = open(basename + ".txt")
	txt = file.read()
	file.close()
    except:
        return ret_val(2, "unable to read text file %s.txt" % basesname)

    return ret_val(0, txt)

def do_one_file(job_queue, done_queue, thread_id):
    while True:
        url, codelang, key = job_queue.get()
        if url == None:
            print "Stopping thread"
            return
        print "start threaded job"
        # done this way to get a more accurate status, we want to know
        # which process are running and waiting so we signal the status change.
        done_queue.put( (None, key, True) )
        json_text = ocr_image(url, codelang, thread_id)
        done_queue.put( (json_text, key, False) )
        print "stop threaded job"

def start_threads():
    num_worker_threads = 2
    thread_array = []
    job_queue = multiprocessing.Queue(num_worker_threads * 16)
    done_queue = multiprocessing.Queue()
    args = (job_queue, done_queue)
    for i in range(num_worker_threads):
        print "starting thread"
        t = multiprocessing.Process(target=do_one_file, args=args + (i, ))
        t.daemon = True
        t.start()
        thread_array.append(t)

    return job_queue, done_queue

def main():
    thread.start_new_thread(bot_listening,())
    job_queue, done_queue = start_threads()
    key = 1L
    dict_query = {}
    
    while 1:

        if len(task_queue):
            url, lang, user, t, conn = task_queue[-1]
        else:
            time.sleep(1)

            while not done_queue.empty():
                json_text, done_key, running = done_queue.get()
                if running:
                    print "pop status change"
                    dict_query[done_key][5] = True
                else:
                    print "pop job"
                    user, url, lang, time1, conn, running = dict_query[done_key]
                    conn.send(json_text)
                    conn.close()
                    time2 = time.time()
                    print date_s(time2)+user+" "+lang+" %s (%.2f)"%(url.split('/')[-1], time2-time1)
                    del dict_query[done_key]
            continue

        if url == 'status':
                print date_s(t) +" STATUS"
                conn.send("OCR daemon is running. %d jobs in queue.<br/><hr/>"%len(dict_query))
                for val in dict_query.itervalues():
                    # t user lang url
                    if val[5]:
                        conn.send(date_s(val[3])+' '+val[0]+" "+val[2]+" "+val[1].split('/')[-1]+" running<br/>")
                    else:
                        conn.send(date_s(val[3])+' '+val[0]+" "+val[2]+" "+val[1].split('/')[-1]+" waiting<br/>")
                conn.close()
        else:
            print "push job"
            dict_query[key] = [ user, url, lang, time.time(), conn, False ]
            job_queue.put((url, lang, key))
            key += 1

	task_queue.pop()

if __name__ == "__main__":
    main()
