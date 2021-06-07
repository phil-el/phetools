#!/usr/bin/python3
# GPL V2, author phe                                                            
__module_name__ = "extract_text_layer_daemon"
__module_version__ = "1.0"
__module_description__ = "extract text layer daemon"

import sys
import os
import _thread
import time

import pywikibot

from common import tool_connect
from common import lifo_cache
from common import job_queue
from common import common_html
from common.pywikibot_utils import safe_put
from match_and_split import align

sys.path.append(os.path.expanduser('~/wikisource'))

E_ERROR = 1
E_OK = 0


def ret_val(error, text):
    if error:
        print(f"Error: {error}, {text}")
    return {'error': error, 'text': text}


def do_extract(mysite, maintitle, user, codelang, cache):
    prefix = mysite.proofread_page_ns.custom_name
    if not prefix:
        return ret_val(E_ERROR, "no prefix")

    djvuname = maintitle.replace(' ', '_')
    print(djvuname)

    text_layer = align.get_djvu(cache, mysite, djvuname, True)
    if not text_layer:
        return ret_val(E_ERROR, "unable to retrieve text layer")

    text = ''
    for pos, page_text in enumerate(text_layer):
        text += f'==[[{prefix}:{maintitle}/{pos + 1}]]==\n'
        text += page_text + '\n'

    page = pywikibot.Page(mysite, f'User:{user}/Text')
    safe_put(page, text, comment='extract text')

    return ret_val(E_OK, "")


def html_for_queue(queue):
    html = ''
    for mtitle, codelang, user, _time, tools, conn in queue:
        try:
            msite = pywikibot.Site(codelang, 'wikisource')
            index_prefix = msite.proofread_index_ns.custom_name
            page = pywikibot.Page(msite, index_prefix + ':' + mtitle)
            path = msite.nice_get_address(page.title(asUrl=True))
            url = f'{msite.protocol()}://{msite.hostname()}{path}'
        except:
            url = ''
        html += f'{date_s(_time)} {user} {codelang} <a href="{url}">{mtitle}</a><br/>'
    return html


def do_status(queue):
    queue = queue.copy_items(True)

    html = common_html.get_head('Extract text layer')
    html += "<body><div>The robot is running.<br/><hr/>"
    html += f"<br/>{len(queue)} jobs in extract queue.<br/>"
    html += html_for_queue(queue)
    html += '</div></body></html>'
    return html


def bot_listening(queue):
    print(date_s(time.time()) + ' START')

    tools = tool_connect.ToolConnect('extract_text_layer', 45132)

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

            if cmd == 'extract':
                queue.put(title, lang, user, t, tools, conn)
            elif cmd == 'status':
                html = do_status(queue)
                tools.send_text_reply(conn, html)
                conn.close()
            elif cmd == 'ping':
                tools.send_reply(conn, ret_val(E_OK, 'pong'))
                conn.close()
            else:
                tools.send_reply(conn, ret_val(E_ERROR, f'unknown command: {cmd}'))
                conn.close()

    finally:
        tools.close()
        print("STOP", file=sys.stderr)


def date_s(at):
    t = time.gmtime(at)
    return time.strftime('[%d/%m/%Y:%H:%M:%S]', t)


def job_thread(queue, cache):
    while True:
        title, codelang, user, t, tools, conn = queue.get()

        time1 = time.time()
        out = ''
        try:
            mysite = pywikibot.Site(codelang, 'wikisource')
        except:
            out = ret_val(E_ERROR, f'site error: {codelang}')
            mysite = False

        if mysite:
            out = do_extract(mysite, title, user, codelang, cache)

        if tools and conn:
            tools.send_reply(conn, out)
            conn.close()

        time2 = time.time()
        print(f'{date_s(time2)}{title} {user} {codelang} {time2 - time1:.2f}')

        queue.remove()


if __name__ == "__main__":
    try:
        cache_dir = 'extract_text_layer'
        if not os.path.exists(os.path.expanduser('~/cache/' + cache_dir)):
            os.mkdir(os.path.expanduser('~/cache/' + cache_dir))
        cache = lifo_cache.LifoCache(cache_dir)
        queue = job_queue.JobQueue()
        _thread.start_new_thread(job_thread, (queue, cache))
        bot_listening(queue)
    except KeyboardInterrupt:
        pywikibot.stopme()
        os._exit(1)
    finally:
        pywikibot.stopme()
