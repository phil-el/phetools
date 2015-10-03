#!/usr/bin/python
# -*- coding: utf-8 -*-
# GPL V2, author thomasv1 at gmx dot de, phe

__module_name__ = "match_and_split_daemon"
__module_version__ = "1.0"
__module_description__ = "match and split daemon"

import sys
import tool_connect
import lifo_cache
from ws_namespaces import page as page_prefixes
import os
import re
import thread
import time
import align
import common_html
import utils
import signal
import job_queue

import pywikibot

from pywikibot_utils import safe_put

E_ERROR = 1
E_OK = 0

# parameters from <pagelist />, used as a cache too.
pl_dict = {}

def rddm_name(year, volume):
    return "Revue des Deux Mondes - %s - tome %s.djvu" % (year, volume)

def get_pl(year, vol):
    global pl_dict
    key = year + "," + vol
    pl = pl_dict.get(key)
    if pl != None:
        return pl

    site = pywikibot.Site('fr', 'wikisource')
    indexpage = pywikibot.Page(site, "Livre:" + rddm_name(year, vol))
    text = indexpage.get()
    m = re.search("(?ms)<pagelist\s+(.*?)/>",text)
    if m:
        el = m.group(1).split()
        l = []
        for item in el:
            mm = re.match("(\d+)=(\d+)",item)
            if mm:
                l.append( (int(mm.group(1)), int(mm.group(2)) ) )

        # FIXME: default sort function should be enough
        l.sort( lambda x,y: cmp(x[0],y[0]) )
        pl_dict[key] = l
    else:
        pl_dict[key] = {}
    return pl_dict[key]

def offset_pagenum(pl, page):
    offset = 0
    for item in pl :
        if page >= item[1]:
            offset = item[0] - item[1]
    return offset + page

def repl(m):
    year = m.group(1)
    vol = m.group(2)
    page = int(m.group(3))
    pagenum = offset_pagenum(get_pl(year, vol), page)
    return "==[[Page:" + rddm_name(year, vol) + "/%d]]==\n" % pagenum


def ret_val(error, text):
    if error:
        print "Error: %d, %s" % (error, text)
    return  { 'error' : error, 'text' : text }

# FIXME, here and everywhere, can't we use mysite.lang and mysite.family.name
# to remove some parameters, does this work for old wikisource?
def do_match(mysite, maintitle, user, codelang):
    prefix = page_prefixes['wikisource'].get(codelang)
    if not prefix:
        return ret_val(E_ERROR, "no prefix")

    page = pywikibot.Page(mysite, maintitle)
    try:
        text = page.get()
    except:
        utils.print_traceback("failed to get page")
        return ret_val(E_ERROR, "failed to get page")

    if text.find("{{R2Mondes")!=-1:
        global pl_dict
        pl_dict = {}
        p0 = re.compile("\{\{R2Mondes\|(\d+)\|(\d+)\|(\d+)\}\}\s*\n")
        try:
            new_text = p0.sub(repl, text)
        except pywikibot.NoPage:
            return ret_val(E_ERROR, "Erreur : impossible de trouver l'index")
        p = re.compile('==\[\[Page:([^=]+)\]\]==\n')

        cache = lifo_cache.LifoCache('match_and_split_text_layer')
        bl= p.split(new_text)
        for i in range(len(bl)/2):
            title  = bl[i*2+1]
            content = bl[i*2+2]
            filename, pagenum = title.split('/')
            if i == 0:
                cached_text = align.get_djvu(cache, mysite, filename, True)
            else:
                cached_text = align.get_djvu(cache, mysite, filename, False)
            if not cached_text:
                return ret_val(E_ERROR, "Erreur : fichier absent")
            if content.find("R2Mondes") != -1:
                p0 = re.compile("\{\{R2Mondes\|\d+\|\d+\|(\d+)\}\}\s*\n")
                bl0 = p0.split(text)
                title0 = bl0[i*2+1].encode("utf8")
                return ret_val(E_ERROR, "Erreur : Syntaxe 'R2Mondes' incorrecte, dans la page "+title0)
            r = align.match_page(content, cached_text[int(pagenum)-1])
            print "%s %s  : %f"%(filename, pagenum, r)
            if r < 0.1:
                return ret_val(E_ERROR, "Erreur : Le texte ne correspond pas, page %s" % pagenum)
        #the page is ok
        new_text = re.sub(u'<references[ ]*/>', u'', new_text)
        new_text = re.sub(u'[ ]([,])', u'\\1', new_text)
        new_text = re.sub(u'([^.])[ ]([,.])', u'\\1\\2', new_text)
        new_text = re.sub(u'\.\.\.', u'…', new_text)

        new_text = re.sub(u'([^ \s])([;:!?])', u'\\1 \\2', new_text)
        new_text = re.sub(u'([«;:!?])([^ \s…])', u'\\1 \\2', new_text)
        # separated from the previous regexp else "word!»" overlap
        new_text = re.sub(u'([^ \s])([»])', u'\\1 \\2', new_text)

        # workaround some buggy text
        new_text = re.sub(u'([;:!?»]) \n', u'\\1\n', new_text)
        new_text = re.sub(u'([;:!?»])\'\'([ \n])', u'\\1\'\'\\2', new_text)
        # <&nbsp;><space>
        #new_text = re.sub(u'  ([;:!?»])', u' \\1', new_text)
        #new_text = re.sub(u' ([;:!?»])', u' \\1', new_text)
        new_text = re.sub(u'([;:!?»]) <br />', u'\\1<br />', new_text)
        new_text = new_text.replace(u'Page : ', u'Page:')
        new_text = new_text.replace(u'\n: ', u'\n:')
        new_text = new_text.replace(u'\n:: ', u'\n::')
        new_text = new_text.replace(u'\n::: ', u'\n:::')
        new_text = new_text.replace(u'\n:::: ', u'\n::::')
        new_text = new_text.replace(u'\n::::: ', u'\n:::::')
        new_text = re.sub(u'1er (janvier|février|avril|mars|mai|juin|juillet|août|septembre|octobre|novembre|décembre)', u'1{{er}} \\1', new_text)
        new_text = re.sub(u'([0-9])e ', u'\\1{{e}} ', new_text)
        #text = re.sub(u'([;:!?»]) <div>\n', u'\\1\n', new_text)

        # try to move the title inside the M&S
        match_title = re.search(u"{{[Jj]ournal[ ]*\|*(.*?)\|", new_text)
        if match_title:
            pos = re.search(u'==(.*?)==', new_text)
            if pos:
                new_text = new_text[0:pos.end(0)] + u'\n{{c|' + match_title.group(1) + u'|fs=140%}}\n\n\n' + new_text[pos.end(0):]

        safe_put(page,new_text,user+": match")
        jobs['number_of_split_job'] += 1
        # FIXME: can we pass the request here and use a callback in the js?
        # FIXME: server is None?
        jobs['split_queue'].put(maintitle, codelang, user, time.time(), None, None, None)
        # FIXME: that's an abuse of E_ERROR
        return ret_val(E_ERROR, "ok : transfert en cours.")

    prefix = prefix.decode('utf-8')
    p = re.compile("==__MATCH__:\[\[" + prefix + ":(.*?)/(\d+)\]\]==")
    m = re.search(p,text)
    if m:
        djvuname = m.group(1)
        number = m.group(2)
        pos = text.find(m.group(0))
        head = text[:pos]
        text = text[pos+len(m.group(0)):]
    else:
        return ret_val(E_ERROR, "match tag not found")

    pywikibot.output(djvuname + " " + number)
    try:
        number = int(number)
    except:
        return ret_val(E_ERROR, "illformed __MATCH__: no page number ?")

    cache = lifo_cache.LifoCache('match_and_split_text_layer')
    cached_text = align.get_djvu(cache, mysite, djvuname, True)
    if not cached_text:
        return ret_val(E_ERROR, "unable to read djvu, if the File: exists, please retry")

    data = align.do_match(text, cached_text, djvuname, number, verbose = False, prefix = prefix)
    if not data['error']:
        safe_put(page, head + data['text'], user + ": match")
        data['text'] = ""

    return data

def do_split(mysite, rootname, user, codelang):
    prefix = page_prefixes['wikisource'].get(codelang)
    if not prefix:
        return ret_val(E_ERROR, "no Page: prefix")
    prefix = prefix.decode('utf-8')

    try:
        page = pywikibot.Page(mysite, rootname)
        text = page.get()
    except:
        return ret_val(E_ERROR, "unable to read page")

    p = re.compile('==\[\[(' + prefix + ':[^=]+)\]\]==\n')
    bl = p.split(text)
    titles = '\n'

    group = ""
    do_refs = False

    fromsection = ""
    tosection = ""

    for i in range(len(bl)/2):

        title  = bl[i*2+1]
        content = bl[i*2+2]

        if content.find("<ref") != -1 :
            do_refs = True

        #for illegalChar in ['#', '<', '>', '[', ']', '|', '{', '}', '\n', u'\ufffd']:
        #    if illegalChar in title:
        #        title = title.replace(illegalChar,'_')

        #always NOPREFIX
        pagetitle = title

        content = content.rstrip("\n ")

        pl = pywikibot.Page(mysite, pagetitle)

        m =  re.match(prefix + ':(.*?)/(\d+)', pagetitle)
        if m:
            filename = m.group(1)
            pagenum = int(m.group(2))
            if not group:
                group = filename
                pfrom = pagenum
                pto = pfrom
            else:
                if filename != group:
                    titles = titles + "<pages index=\"%s\" from=%d to=%d />\n"%(group,pfrom,pto)
                    group = filename
                    pfrom = pagenum
                    pto = pfrom
                elif pagenum != pto + 1:
                    titles = titles + "<pages index=\"%s\" from=%d to=%d />\n"%(group,pfrom,pto)
                    group = filename
                    pfrom = pagenum
                    pto = pfrom
                else:
                    pto = pagenum
        else:
            if group:
                titles = titles + "<pages index=\"%s\" from=%d to=%d />\n"%(group,pfrom,pto)
                group = False

            titles = titles + "{{"+pagetitle+"}}\n"

        #prepend br
        if content and content[0]=='\n':
            content = '<nowiki />\n'+content

        if pl.exists():
            old_text = pl.get()
            refs = pl.getReferences(onlyTemplateInclusion = True)
            numrefs = 0
            for ref in refs:
                numrefs += 1

            #first and last pages : check if they are transcluded
            if numrefs > 0 :
                m = re.match("<noinclude>(.*?)</noinclude>(.*)<noinclude>(.*?)</noinclude>",old_text,re.MULTILINE|re.DOTALL)
                if m and (i == 0 or i == (len(bl)/2 -1)):
                    print "creating sections"
                    old_text = m.group(2)
                    if i == 0:
                        first_part = old_text
                        second_part = content
                        fromsection="fromsection=s2 "
                    else:
                        first_part = content
                        second_part = old_text
                        tosection="tosection=s1 "

                    content = "<noinclude>"+m.group(1)+"</noinclude><section begin=s1/>"+first_part+"<section end=s1/>\n----\n" \
                        + "<section begin=s2/>"+second_part+"<section end=s2/><noinclude>"+m.group(3)+"</noinclude>"
            else:
                m = re.match("<noinclude><pagequality level=\"1\" user=\"(.*?)\" />(.*?)</noinclude>(.*)<noinclude>(.*?)</noinclude>",
                             old_text,re.MULTILINE|re.DOTALL)
                if m :
                    print "ok, quality 1, first try"
                    content = "<noinclude><pagequality level=\"1\" user=\"" + m.group(1) + "\" />"+m.group(2)+"</noinclude>"+content+"<noinclude>"+m.group(4)+"</noinclude>"
                    m2 = re.match("<noinclude>\{\{PageQuality\|1\|(.*?)\}\}(.*?)</noinclude>(.*)<noinclude>(.*?)</noinclude>",
                                  old_text,re.MULTILINE|re.DOTALL)
                    if m2 :
                        # FIXME: shouldn't use an hardcoded name here
                        print "ok, quality 1, second try"
                        content = "<noinclude><pagequality level=\"1\" user=\"Phe-bot\" />"+m2.group(2)+"</noinclude>"+content+"<noinclude>"+m2.group(4)+"</noinclude>"

        else:
            header = u'<noinclude><pagequality level="1" user="Phe-bot" /><div class="pagetext">\n\n\n</noinclude>'
            footer = u'<noinclude>\n<references/></div></noinclude>'
            content = header + content + footer
            

        safe_put(pl,content,user+": split")

    if group:
        titles = titles + "<pages index=\"%s\" from=%d to=%d %s%s/>\n"%(group,pfrom,pto,fromsection,tosection)

    if fromsection:
        rtext = ref.get()
        m = re.search("<pages index=\"(.*?)\" from=(.*?) to=(.*?) (fromsection=s2 |)/>",rtext)
        if m and m.group(1)==group:
            rtext = rtext.replace(m.group(0), m.group(0)[:-2]+"tosection=s1 />" )
            print "new rtext"
            safe_put(ref,rtext,user+": split")

    if tosection:
        rtext = ref.get()
        m = re.search("<pages index=\"(.*?)\" from=(.*?) to=(.*?) (tosection=s1 |)/>",rtext)
        if m and m.group(1)==group:
            rtext = rtext.replace(m.group(0), m.group(0)[:-2]+"fromsection=s2 />" )
            print "new rtext"
            safe_put(ref,rtext,user+": split")

    if do_refs:
        titles += "----\n<references/>\n"

    header = bl[0]
    safe_put(page,header+titles,user+": split")

    return ret_val(E_OK, "")


jobs = None

# title, codelang, user, t, tools, server, conn
def html_for_queue(queue):
    html = ''
    for i in queue:
        mtitle = i[0]
        codelang = i[1]
        try:
            msite = pywikibot.Site(codelang, 'wikisource')
            page = pywikibot.Page(msite, mtitle)
            path = msite.nice_get_address(page.title(asUrl = True))
            url = '%s://%s%s' % (msite.protocol(), msite.hostname(), path)
        except:
            url = ""
        html += date_s(i[3])+' '+i[2]+" "+i[1]+" <a href=\""+url+"\">"+i[0]+"</a><br/>"
    return html

def do_status():
    m_queue = jobs['match_queue'].copy_items(True)
    s_queue = jobs['split_queue'].copy_items(True)

    html = common_html.get_head('Match and split')

    html += u"<body><div>the robot is running.<br/><hr/>"
    html += u"<br/>%d jobs in match queue.<br/>" % len(m_queue)
    html += html_for_queue(m_queue)
    html += u"<br/>%d jobs in split queue.<br/>" % len(s_queue)
    html += html_for_queue(s_queue)
    html += u"<br/>%(number_of_match_job)d match, %(number_of_split_job)d split since server start<br/>" % jobs
    html += u'</div></body></html>'

    return html

def stop_queue(queue):
    new_queue = job_queue.JobQueue()
    items = queue.copy_items()
    for title, lang, user, t, tools, server, conn in items:
        new_queue.put(title, lang, user, t, None, server, None)
        if conn:
            conn.close()
    return new_queue

# either called through a SIGUSR2 or a finally clause.
def on_exit(sig_nr, frame):
    print "STOP"

    jobs['match_queue'] = stop_queue(jobs['match_queue'])
    jobs['split_queue'] = stop_queue(jobs['split_queue'])

    #utils.save_obj('wsdaemon.jobs', jobs)

def bot_listening():

    print date_s(time.time())+ " START"

    tools = tool_connect.ToolConnect('match_and_split', 45130)

    try:
        while True:
            request, conn = tools.wait_request()

            try:
                print request

                cmd = request['cmd']
                title = request.get('title', '')
                lang = request.get('lang', '')
                user = request.get('user', '')
                server = request.get('server', '')
            except:
                ret = ret_val(E_ERROR, "invalid request")
                tools.send_reply(conn, ret)
                conn.close()
                continue

            t = time.time()
            user = user.replace(' ', '_')

            print (date_s(t) + " REQUEST " + user + ' ' + lang + ' ' + cmd + ' ' + title + ' ' + server).encode('utf-8')

            if cmd == "status":
                html = do_status()
                tools.send_text_reply(conn, html)
                conn.close()
            elif cmd == "match":
                jobs['number_of_match_job'] += 1
                jobs['match_queue'].put(title, lang, user, t, tools, server, conn)
            elif cmd == "split":
                jobs['number_of_split_job'] += 1
                jobs['split_queue'].put(title, lang, user, t, tools, server, conn)
            elif cmd == 'ping':
                tools.send_reply(conn, ret_val(E_OK, 'pong'))
                conn.close()
            else:
                tools.send_reply(conn, ret_val(E_ERROR, "unknown command: " + cmd))
                conn.close()

    finally:
        tools.close()
        on_exit(0, None)

def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])

def job_thread(queue, func):
    while True:
        title, codelang, user, t, tools, server, conn = queue.get()
        if not server:
            server = 'unknown server'

        time1 = time.time()
        out = ''
        try:
            mysite = pywikibot.Site(codelang, 'wikisource')
        except:
            out = ret_val(E_ERROR, "site error: " + repr(codelang))
            mysite = False

        if mysite:
            out = func(mysite, title, user, codelang)

        if tools and conn:
            tools.send_reply(conn, out)
            conn.close()

        time2 = time.time()
        print (date_s(time2) + ' ' + title + ' ' + user + ' ' +  codelang + " " + server + " (%.2f)" % (time2-time1)).encode('utf-8')

        queue.remove()

def default_jobs():
    return { 
        'match_queue' : job_queue.JobQueue(),
        'split_queue' : job_queue.JobQueue(),
        'number_of_match_job' : 0,
        'number_of_split_job' : 0
        }

if __name__ == "__main__":
    try:
        cache_dir = 'match_and_split_text_layer'
        if not os.path.exists(os.path.expanduser('~/cache/' + cache_dir)):
            os.mkdir(os.path.expanduser('~/cache/' + cache_dir))
        # qdel send a SIGUSR2 if -notify is used when starting the job.
        #signal.signal(signal.SIGUSR2, on_exit)
        try:
            jobs = utils.load_obj("wsdaemon.jobs")
        except:
            jobs = default_jobs()

        thread.start_new_thread(job_thread, (jobs['match_queue'], do_match))
        thread.start_new_thread(job_thread, (jobs['split_queue'], do_split))
        bot_listening()
    except KeyboardInterrupt:
        pywikibot.stopme()
        os._exit(1)
    finally:
        pywikibot.stopme()
