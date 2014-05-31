#!/usr/bin/python
# GPL V2, author phe

__module_name__ = "dummy_robot"
__module_version__ = "1.0"
__module_description__ = "dummy robot"

import sys
sys.path.append('/data/project/phetools/phe/common')
import tool_connect
import common_html

import os
import thread
import time
import urllib
import job_queue

E_ERROR = 1
E_OK = 0

def ret_val(error, text):
    if error:
        print >> sys.stderr, "Error: %d, %s" % (error, text)
    return  { 'error' : error, 'text' : text }

def do_exec(title, cmd):
    if cmd == 'timeout':
        time.sleep(60)
        return ret_val(E_ERROR, "timeout: 60 sec: " + title)

    return ret_val(E_OK, "exec ok: " + title)

# cmd title t tools conn
def html_for_queue(queue):
    html = u''
    for i in queue:
        mtitle = i[1]

        html += date_s(i[1]) + ' ' + mtitle + "<br/>"
    return html

def do_status(queue):
    queue = queue.copy_items(queue)

    html = common_html.get_head(u'Dummy robot')
    html += u"<body><div>The robot is running.<br/><hr/>"
    html += u"<br/>%d jobs in dummy robot queue.<br/>" % len(queue)
    html += html_for_queue(queue)
    html += u'</div></body></html>'
    return html

def bot_listening(queue):

    print date_s(time.time()) + " START"

    tools = tool_connect.ToolConnect('dummy_robot', 45139)

    try:
        while True:
            request, conn = tools.wait_request()

            try:
                print request

                cmd = request['cmd']
                title = request.get('title', '')
                title = unicode(urllib.unquote(title.encode('utf-8')), 'utf-8')
            except:
                ret = ret_val(E_ERROR, "invalid request")
                tools.send_reply(conn, ret)
                conn.close()
                continue

            t = time.time()

            print (date_s(t) + " REQUEST " + cmd + ' ' + title).encode('utf-8')

            if cmd in [ "exec", "timeout" ]:
                queue.put(cmd, title, t, tools, conn)
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


def job_thread(queue, func):
    while True:
        cmd, title, t, tools, conn = queue.get()

        time1 = time.time()

        out = func(title, cmd)

        if tools and conn:
            tools.send_reply(conn, out)
            conn.close()

        time2 = time.time()
        print (date_s(time2) + ' ' + title + " (%.2f)" % (time2-time1)).encode('utf-8')

        queue.remove()


if __name__ == "__main__":
    try:
        queue = job_queue.JobQueue()
        thread.start_new_thread(job_thread, (queue, do_exec))
        bot_listening(queue)
    except KeyboardInterrupt:
        os._exit(1)
#    finally:
#        pywikibot.stopme()
