#!/usr/bin/python3
# GPL V2, author phe

__module_name__ = "verify_match_daemon"
__module_version__ = "1.0"
__module_description__ = "verify match daemon"

import sys
from common import tool_connect
from common import job_queue
from common import lifo_cache
from common import utils

import os
import _thread
import time

import pywikibot
from common import common_html
import verify_match

E_ERROR = 1
E_OK = 0


def ret_val(error, text):
    if error:
        print(f"Error: {error}, {text}", file=sys.stderr)
    return {'error': error, 'text': text}


def do_match(mysite, cached_diff, cached_text, maintitle, user):
    opt = verify_match.default_options()
    opt.site = mysite
    maintitle = maintitle.replace('_', ' ')

    verify_match.main(maintitle, cached_diff, cached_text, opt)

    return ret_val(E_OK, "")


# title user lang t tools conn
def html_for_queue(queue):
    html = ''
    for i in queue:
        mtitle = i[0]
        codelang = i[1]
        try:
            msite = pywikibot.Site(codelang, 'wikisource')
            page = pywikibot.Page(msite, mtitle)
            path = msite.nice_get_address(page.title(asUrl=True))
            url = '%s://%s%s' % (msite.protocol(), msite.hostname(), path)
        except BaseException:
            utils.print_traceback()
            url = ""

        html += date_s(i[3]) + ' ' + i[2] + " " + i[1] + " <a href=\"" + url + "\">" + i[0] + "</a><br/>"
    return html


def do_status(queue):
    queue = queue.copy_items(True)

    html = common_html.get_head('Verify match')
    html += "<body><div>The robot is running.<br/><hr/>"
    html += "<br/>%d jobs in verify match queue.<br/>" % len(queue)
    html += html_for_queue(queue)
    html += '</div></body></html>'
    return html


def bot_listening(queue):
    print(date_s(time.time()) + " START")

    tools = tool_connect.ToolConnect('verify_match', 45131)

    try:
        while True:
            request, conn = tools.wait_request()

            try:
                print(request)

                cmd = request['cmd']
                title = request.get('title', '')
                lang = request.get('lang', '')
                user = request.get('user', '')
            except:
                ret = ret_val(E_ERROR, "invalid request")
                tools.send_reply(conn, ret)
                conn.close()
                continue

            t = time.time()
            user = user.replace(' ', '_')

            print(f'{date_s(t)} REQUEST {user} {lang} {cmd} {title}')

            if cmd == "verify":
                queue.put(title, lang, user, t, tools, conn)
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
        print("STOP", file=sys.stderr)


def date_s(at):
    t = time.gmtime(at)
    return time.strftime("%d/%m/%Y:%H:%M:%S", t)


def job_thread(queue):
    cache_dir1 = 'verify_match_diff'
    cached_diff = lifo_cache.LifoCache(cache_dir1)
    cache_dir2 = 'verify_match_text_layer'
    cached_text = lifo_cache.LifoCache(cache_dir2)
    while True:
        title, codelang, user, t, tools, conn = queue.get()

        time1 = time.time()
        out = ''
        try:
            mysite = pywikibot.Site(codelang, 'wikisource')
        except:
            out = ret_val(E_ERROR, "site error: " + repr(codelang))
            mysite = False

        if mysite:
            out = do_match(mysite, cached_diff, cached_text, title, user)

        if tools and conn:
            tools.send_reply(conn, out)
            conn.close()

        time2 = time.time()
        print(f'{date_s(time2)}{title} {user} {codelang} ({time2 - time1}.2f)')

        queue.remove()


if __name__ == "__main__":
    cache_dir1 = 'verify_match_diff'
    if not os.path.exists(os.path.expanduser('~/cache/' + cache_dir1)):
        os.mkdir(os.path.expanduser('~/cache/' + cache_dir1))
    cache_dir2 = 'verify_match_text_layer'
    if not os.path.exists(os.path.expanduser('~/cache/' + cache_dir2)):
        os.mkdir(os.path.expanduser('~/cache/' + cache_dir2))
    try:
        queue = job_queue.JobQueue()
        _thread.start_new_thread(job_thread, (queue,))
        bot_listening(queue)
    except KeyboardInterrupt:
        pywikibot.stopme()
        os._exit(1)
    finally:
        pywikibot.stopme()
