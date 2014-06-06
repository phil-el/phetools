#!/usr/bin/python
# GPL V2, author thomasv1 at gmx dot de, phe at nowhere

__module_name__ = "wikisourceocr"
__module_version__ = "1.0"
__module_description__ = "wikisource ocr bot"

import sys
sys.path.append('/data/project/phetools/phe/common')

import os
import thread
import time
import hashlib
import re
import common_html
import ocr
import utils
import lifo_cache
import job_queue
import tool_connect
import urllib

E_OK = 0
E_ERROR = 1

# url user lang t tools conn
def html_for_queue(queue):
    html = u''
    for i in queue:
        url = i[0]
        html += date_s(i[3])+' '+i[2]+" "+i[1]+" "+url+"<br />"
    return html

def do_status(queue):
    queue = queue.copy_items(True)

    html = common_html.get_head('OCR service')
    html += '<body><div>The ocr robot is runnning.<br /><hr />'
    html += "%d jobs in queue.<br/>" % len(queue)
    html += html_for_queue(queue)
    html += '</div></body></html>'

    return html

def next_pagename(match):
    return '%s/page%d-%spx-%s' % (match.group(1), int(match.group(2)) + 1, match.group(3), match.group(4))

def next_url(url):
    return re.sub(u'^(.*)/page(\d+)-(\d+)px-(.*)$', next_pagename, url)

def bot_listening(queue):

    print date_s(time.time()) + " START"

    tools = tool_connect.ToolConnect('ws_ocr_daemon', 45133)

    try:
        while True:
            request, conn = tools.wait_request()

            try:
                url = request.get('url', '')
                lang = request.get('lang', '')
                user = request.get('user', '')
                cmd = request['cmd']
            except:
                ret = ret_val(E_ERROR, "invalid request")
                tools.send_reply(conn, ret)
                conn.close()
                continue

            t = time.time()
            print (date_s(t) + " REQUEST " + user + ' ' + lang + ' ' + cmd + ' ' + url).encode('utf-8')

            if cmd == "ocr":
                queue.put(url, lang, user, t, tools, conn)

                next_page_url = next_url(url)

                queue.put(next_page_url, lang, user, t, None, None)

            elif cmd == 'status':
                html = do_status(queue)
                tools.send_text_reply(conn, html)
                conn.close()
            elif cmd == 'ping':
                tools.send_reply(conn, ret_val(E_OK, 'pong'))
                conn.close()
            else:
                tools.send_reply(conn, ret_val(E_ERROR, "unknown command: " + cmd))
                conn.close()
    finally:
	tools.close()


def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])

def ret_val(error, text):
    if error:
        print "Error: %d, %s" % (error, text)
    return  {'error' : error, 'text' : text }

def image_key(url):
    # FIXME: it'll better to use the sha1 of the image itself.
    m = hashlib.sha1()
    m.update(url)
    return m.hexdigest()

def ocr_image(cache, url, codelang):

    url = url.encode('utf-8')

    cache_key = image_key(url)

    text = cache.get(cache_key)
    if text:
        return ret_val(0, text)

    lang = ocr.tesseract_languages.get(codelang, 'eng')

    basename = '/data/project/phetools/tmp/tesseract/image_%s' % cache_key

    image_filename = basename + ".jpg"

    utils.copy_file_from_url(url, image_filename)
    if not os.path.exists(image_filename):
        return ret_val(1, "could not download url: %s" % url)

    text = ocr.ocr(image_filename, basename, lang)
    if text == None:
        return ret_val(2, "ocr failed")

    os.remove(image_filename)
    if text:
        os.remove(basename + ".txt")

    cache.set(cache_key, text)

    return ret_val(0, text)

def next_pagename(match):
    return '%s/page%d-%spx-%s' % (match.group(1), int(match.group(2)) + 1, match.group(3), match.group(4))

def job_thread(queue):
    # FIXME: the cache must be passed to job_thread() and bot_listening()
    # to allow cache hit in bot_listening(), actually even if a page is in the
    # cache user will get an answer only when the top of job queue will be its
    # request. Atm the cache is not thread safe so, make it thread safe first.
    cache = lifo_cache.LifoCache('tesseract_page')
    while True:
        url, codelang, user, t, tools, conn = queue.get()

        time1 = time.time()
        out = ''

        out = ocr_image(cache, url, codelang)

        if tools and conn:
            tools.send_reply(conn, out)
            conn.close()

        time2 = time.time()
        print (date_s(time2) + ' ' + url + ' ' + user + " " + codelang + " (%.2f)" % (time2-time1)).encode('utf-8')

        queue.remove()

if __name__ == "__main__":
    try:
        queue = job_queue.JobQueue()
        thread.start_new_thread(job_thread, (queue, ))
        bot_listening(queue)
    except KeyboardInterrupt:
        os._exit(1)

