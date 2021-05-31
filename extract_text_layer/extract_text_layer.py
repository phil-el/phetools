#!/usr/bin/python
# GPL V2, author phe                                                            
__module_name__ = "extract_text_layer_daemon"
__module_version__ = "1.0"
__module_description__ = "extract text layer daemon"

import sys
import os

sys.path.append(os.path.expanduser('~/wikisource'))
from ws_namespaces import page as page_prefixes, index as index_prefixes
from common import tool_connect
from common import lifo_cache
from common import job_queue

import thread
import time

from match_and_split import align
import pywikibot
from common import common_html

from common.pywikibot_utils import safe_put

E_ERROR = 1
E_OK = 0


def ret_val(error, text):
    if error:
        print(f"Error: {error}, {text}")
    return {'error': error, 'text': text}


def do_extract(mysite, maintitle, user, codelang, cache):
    prefix = unicode(page_prefixes['wikisource'].get(codelang), 'utf-8')
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


# title user lang t tools conn
def html_for_queue(queue):
    html = ''
    for i in queue:
        mtitle = i[0]
        codelang = i[1]
        try:
            msite = pywikibot.getSite(codelang, 'wikisource')
            index_prefix = unicode(index_prefixes['wikisource'].get(codelang), 'utf-8')
            page = pywikibot.Page(msite, index_prefix + ':' + mtitle)
            path = msite.nice_get_address(page.title(asUrl=True))
            url = f'{msite.protocol()}://{msite.hostname()}{path}'
        except:
            url = ""
        html += date_s(i[3]) + ' ' + i[2] + " " + i[1] + " <a href=\"" + url + "\">" + i[0] + "</a><br/>"
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
    return "[%02d/%02d/%d:%02d:%02d:%02d]" % (t[2], t[1], t[0], t[3], t[4], t[5])


def job_thread(queue, cache):
    while True:
        title, codelang, user, t, tools, conn = queue.get()

        time1 = time.time()
        out = ''
        try:
            mysite = pywikibot.getSite(codelang, 'wikisource')
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
        thread.start_new_thread(job_thread, (queue, cache))
        bot_listening(queue)
    except KeyboardInterrupt:
        pywikibot.stopme()
        os._exit(1)
    finally:
        pywikibot.stopme()
