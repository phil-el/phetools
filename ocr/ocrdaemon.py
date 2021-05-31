#!/usr/bin/python3
# GPL V2, author thomasv1 at gmx dot de, phe at nowhere

__module_name__ = "wikisourceocr"
__module_version__ = "1.0"
__module_description__ = "wikisource ocr bot"

import os
import thread
import time
import hashlib
import re
from common import common_html
import ocr
from common import utils
from common import lifo_cache
from common import job_queue
from common import tool_connect

E_OK = 0
E_ERROR = 1


# url user lang t tools conn
def html_for_queue(queue):
    html = ''
    for i in queue:
        url = i[0]
        html += date_s(i[3]) + ' ' + i[2] + " " + i[1] + " " + url + "<br />"
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
    return re.sub(r'^(.*)/page(\d+)-(\d+)px-(.*)$', next_pagename, url)


def bot_listening(queue, cache):
    print(date_s(time.time()) + " START")

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
            print(f'{date_s(t)} REQUEST {user} {lang} {cmd} {url}')

            if cmd == "ocr":
                # bypass the job queue if the ocr is cached to ensure a cached
                # ocr will be returned as soon as possible.
                text = get_from_cache(cache, url, lang)
                if text:
                    tools.send_reply(conn, ret_val(E_OK, text))
                    conn.close()
                else:
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
    return time.strftime("%d/%m/%Y:%H:%M:%S", t)


def ret_val(error, text):
    if error:
        print("Error: %d, %s" % (error, text))
    return {'error': error, 'text': text}


def image_key(url):
    # FIXME: it'll better to use the sha1 of the image itself or rather the
    # sha1 of the djvu/pdf (or both ?).
    m = hashlib.sha1()
    m.update(url)
    return m.hexdigest()


def get_from_cache(cache, url, codelang):
    cache_key = image_key(url)

    return cache.get(cache_key)


def ocr_image(cache, url, codelang):
    # This is checked in bot_listening but must be redone here, so if
    # the ocr for the same page is asked multiple time, we will do the ocr
    # only once.
    text = get_from_cache(cache, url, codelang)
    if text:
        return ret_val(0, text)

    cache_key = image_key(url)

    lang = ocr.tesseract_languages.get(codelang, 'eng')

    basename = os.path.expanduser('~/tmp') + '/tesseract/image_%s' % cache_key

    image_filename = basename + ".jpg"

    try:
        utils.copy_file_from_url(url, image_filename)
    except:
        return ret_val(3, "IOError: %s (invalid url?)" % url)
    if not os.path.exists(image_filename):
        return ret_val(1, "could not download url: %s" % url)

    text = ocr.ocr(image_filename, basename, lang)
    if text is None:
        return ret_val(2, "ocr failed")

    os.remove(image_filename)
    if os.path.exists(basename + ".txt"):
        os.remove(basename + ".txt")

    cache.set(cache_key, text)

    return ret_val(0, text)


def job_thread(queue, cache):
    while True:
        url, codelang, user, t, tools, conn = queue.get()

        time1 = time.time()
        out = ''

        out = ocr_image(cache, url, codelang)

        if tools and conn:
            tools.send_reply(conn, out)
            conn.close()

        time2 = time.time()
        print(f'{date_s(time2)} {url} {user} {codelang} ({time2 - time1}:.2f)')

        queue.remove()


if __name__ == "__main__":
    try:
        cache_dir = 'tesseract_page'
        if not os.path.exists(os.path.expanduser('~/cache/' + cache_dir)):
            os.mkdir(os.path.expanduser('~/cache/' + cache_dir))
        cache = lifo_cache.LifoCache(cache_dir)
        queue = job_queue.JobQueue()
        thread.start_new_thread(job_thread, (queue, cache))
        bot_listening(queue, cache)
    except KeyboardInterrupt:
        os._exit(1)
