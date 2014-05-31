#!/usr/bin/python
# GPL V2, author phe

__module_name__ = "verify_match_daemon"
__module_version__ = "1.0"
__module_description__ = "verify match daemon"

import sys
sys.path.append('/data/project/phetools/phe/match_and_split')
sys.path.append('/data/project/phetools/phe/common')
import tool_connect
import job_queue

import os
import thread
import time

import pywikibot
import common_html
import verify_match
import urllib

E_ERROR = 1
E_OK = 0


def ret_val(error, text):
    if error:
        print >> sys.stderr, "Error: %d, %s" % (error, text)
    return  { 'error' : error, 'text' : text }

def do_match(mysite, maintitle, user):

    opt = verify_match.default_options()
    opt.site = mysite
    maintitle = maintitle.replace(u'_', u' ')

    if verify_match.main(maintitle, opt):
        return ret_val(E_OK, "")
    return ret_val(E_ERROR, "unknown error")

# title user lang t tools conn
def html_for_queue(queue):
    html = u''
    for i in queue:
        mtitle = i[0]
        codelang = i[1]
        try:
            msite = pywikibot.getSite(codelang, 'wikisource')
            page = pywikibot.Page(msite, mtitle)
            path = msite.nice_get_address(page.title(asUrl = True))
            url = '%s://%s%s' % (msite.protocol(), msite.hostname(), path)
        except BaseException as e:
            import traceback
            print >> sys.stderr, str(e)
            print >> sys.stderr, traceback.format_exc()
            url = ""

        html += date_s(i[3])+' '+i[2]+" "+i[1]+" <a href=\""+url+"\">"+i[0]+"</a><br/>"
    return html

def do_status(queue):
    queue = queue.copy_items(True)

    html = common_html.get_head(u'Verify match')
    html += u"<body><div>The robot is running.<br/><hr/>"
    html += u"<br/>%d jobs in verify match queue.<br/>" % len(queue)
    html += html_for_queue(queue)
    html += u'</div></body></html>'
    return html

def bot_listening(queue):

    print date_s(time.time())+ " START"

    tools = tool_connect.ToolConnect('verify_match', 45131)

    try:
        while True:
            request, conn = tools.wait_request()

            try:
                print request

                cmd = request['cmd']
                title = request.get('title', '')
                title = unicode(urllib.unquote(title.encode('utf-8')), 'utf-8')
                lang = request.get('lang', '')
                user = request.get('user', '')
            except:
                ret = ret_val(E_ERROR, "invalid request")
                tools.send_reply(conn, ret)
                conn.close()
                continue

            t = time.time()
            user = user.replace(' ', '_')

            print (date_s(t) + " REQUEST " + user + ' ' + lang + ' ' + cmd + ' ' + title).encode('utf-8')

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
        print >> sys.stderr, "STOP"

def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])


def job_thread(queue):
    while True:
        title, codelang, user, t, tools, conn = queue.get()

        time1 = time.time()
        out = ''
        try:
            mysite = pywikibot.getSite(codelang, 'wikisource')
        except:
            out = ret_val(E_ERROR, "site error: " + repr(codelang))
            mysite = False

        if mysite:
            out = do_match(mysite, title, user)

        if tools and conn:
            tools.send_reply(conn, out)
            conn.close()

        time2 = time.time()
        print (date_s(time2) + title + ' ' + user + " " + codelang + " (%.2f)" % (time2-time1)).encode('utf-8')

        queue.remove()


if __name__ == "__main__":
    try:
        queue = job_queue.JobQueue()
        thread.start_new_thread(job_thread, (queue, ))
        bot_listening(queue)
    except KeyboardInterrupt:
        pywikibot.stopme()
        os._exit(1)
    finally:
        pywikibot.stopme()
