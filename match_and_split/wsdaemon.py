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
#    copyright thomasv1 at gmx dot de

__module_name__ = "wikisourcedaemon"
__module_version__ = "1.0"
__module_description__ = "wikisource daemon"

import match_and_split_config as config

import os
import socket
import re
import thread, time

import align

import wikipedia, pywikibot

mylock = thread.allocate_lock()

# FIXME: try to avoid hard-coding this, pywikipedia know them but often
# pywikipedia code lag a bit behind new namespace creation, get it directly
# from the database (is it possible?) or through the api (but does all
# wikisource have a correct alias for the Page: namespace?)
page_prefixes = {
    'br' : 'Pajenn',
    'ca' : 'P\xc3\xa0gina',
    'de' : 'Seite',
    'en' : 'Page',
    'es' : 'P\xc3\xa1gina',
    'fr' : 'Page',
    'hr' : 'Stranica',
    'hu' : 'Oldal',
    'hy' : '\xd4\xb7\xd5\xbb',
    'it' : 'Pagina',
    'la' : 'Pagina',
    'no' : 'Side',
    'old': 'Page',
    'pl' : 'Strona',
    'pt' : 'P\xc3\xa1gina',
    'ru' : '\xd1\x81\xd1\x82\xd1\x80\xd0\xb0\xd0\xbd\xd0\xb8\xd1\x86\xd0\xb0',
    'sl' : 'Stran',
    'sv' : 'Sida',
    'vec': 'Pagina',
    'vi' : 'Trang',
    'zh' : 'Page',
    }

E_ERROR = "error"
E_OK = "ok"

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

    # This presume wikipedia.setSite() has been called.
    indexpage = wikipedia.Page(wikipedia.getSite(), "Livre:" + rddm_name(year, vol))
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
    return "==[[" + rddm_name(year, vol) + "%d]]==\n" % pagenum


# FIXME: use a real Queue object and avoid polling the queue

# Get a job w/o removing it from the queue. FIXME: probably not the best
# way, if a job can't be handled due to exception and the exception is
# gracefully catched by the worker thread, there is no warranty than the
# job will be removed from the queue, so the worker thread can hang forever
# trying to do something causing an exception. This is not possible actually
# but it's fragile to not remove the job when getting it.
def get_job(lock, queue):
    got_it = False
    while not got_it:
        time.sleep(0.5)
        lock.acquire()
        if match_queue != []:
            title, codelang, user, t, conn = queue[-1]
            got_it = True
        lock.release()

    return title, codelang, user, t, conn

def remove_job(lock, queue):
    lock.acquire()
    queue.pop()
    lock.release()

def add_job(lock, queue, cmd):
    lock.acquire()
    queue.insert(0, cmd)
    lock.release()

# FIXME, here and everywhere, can't we use mysite.lang and mysite.family.name
# to remove some parameters, does this work for old wikisource?
def do_match(mysite, maintitle, user, codelang):
    prefix = page_prefixes.get(codelang)
    if not prefix:
        print "no prefix"
        return E_ERROR

    page = wikipedia.Page(mysite, maintitle)
    try:
        text = page.get()
    except:
        print "failed to get page"
        return E_ERROR

    if text.find("{{R2Mondes")!=-1:
        global pl_dict
        pl_dict = {}
        p0 = re.compile("\{\{R2Mondes\|(\d+)\|(\d+)\|(\d+)\}\}\s*\n")
        try:
            new_text = p0.sub(repl, text)
        except wikipedia.NoPage:
            print "failed to get index page"
            return "Erreur : impossible de trouver l'index"
        p = re.compile('==\[\[Page:([^=]+)\]\]==\n')
        bl= p.split(new_text)
        for i in range(len(bl)/2):
            title  = bl[i*2+1]
            content = bl[i*2+2]
            filename, pagenum = title.split('/')
            filename = align.get_djvu(mysite, filename)
            if not filename:
                return "Erreur : fichier absent"
            if content.find("R2Mondes") != -1:
                p0 = re.compile("\{\{R2Mondes\|\d+\|\d+\|(\d+)\}\}\s*\n")
                bl0 = p0.split(text)
                title0 = bl0[i*2+1].encode("utf8")
                return "Erreur : Syntaxe 'R2Mondes' incorrecte, dans la page "+title0
            r = align.match_page(content, filename, int(pagenum))
            print "%s %s  : %f"%(filename, pagenum, r)
            if r < 0.1:
                return "Erreur : Le texte ne correspond pas, page %s" % pagenum
        #the page is ok
        safe_put(page,new_text,user+": match")
        add_job(lock, split_queue, (maintitle.encode("utf8"), codelang, user.encode("utf8"), time.time(), None))
        return "ok : transfert en cours."

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
        print "match tag not found"
        return E_ERROR

    wikipedia.output(djvuname + " " + number)
    try:
        number = int(number)
    except:
        return E_ERROR

    filename = align.get_djvu(mysite, djvuname, True)
    if not filename:
        return E_ERROR

    output, status = align.do_match(text, filename, djvuname, number, verbose = False, prefix = prefix)
    if status == "ok":
        safe_put(page, head + output, user + ": match")

    return status


def safe_put(page,text,comment):
    if re.match("^[\s\n]*$", text):
        return

    # FIXME, why this is protected by a lock ? if it is only for the setAction,
    # pass the comment directly to put, but is put() thread safe? Actually not
    # a trouble, only one instance of the bot can run but better to check that
    mylock.acquire()
    wikipedia.setAction(comment)

    while 1:
        try:
            status, reason, data = page.put(text)
            if reason != u'OK':
                print "put error", status, reason, data
                time.sleep(10)
                continue
            else:
                break
        except wikipedia.LockedPage:
            print "put error : Page %s is locked?!" % page.aslink().encode("utf8")
            break
        except wikipedia.NoPage:
            print "put error : Page does not exist %s" % page.aslink().encode("utf8")
            break
        except pywikibot.NoUsername:
            print "put error : No user name on wiki %s" % page.aslink().encode("utf8")
            break
        except:
            print "put error: unknown exception"
            time.sleep(5)
            break
    mylock.release()


def do_split(mysite, rootname, user, codelang):
    prefix = page_prefixes.get(codelang)
    if not prefix:
        return E_ERROR
    prefix = prefix.decode('utf-8')

    try:
        page = wikipedia.Page(mysite,rootname)
        text = page.get()
    except:
        return E_ERROR

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

        pl = wikipedia.Page(mysite, pagetitle)

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
                if m and ( i==0 or i==(len(bl)/2 -1) ):
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
                    print "ok, quality 1"
                    content = "<noinclude><pagequality level=\"1\" user=\"" + m.group(1) + "\" />"+m.group(2)+"</noinclude>"+content+"<noinclude>"+m.group(4)+"</noinclude>"
                    m2 = re.match("<noinclude>\{\{PageQuality\|1\|(.*?)\}\}(.*?)</noinclude>(.*)<noinclude>(.*?)</noinclude>",
                                  old_text,re.MULTILINE|re.DOTALL)
                if m2 :
                    # FIXME: shouldn't use an hardcoded name here
                    print "ok, quality 1"
                    content = "<noinclude><pagequality level=\"1\" user=\"ThomasBot\" />"+m2.group(2)+"</noinclude>"+content+"<noinclude>"+m2.group(4)+"</noinclude>"

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

    return E_OK


match_queue = []
split_queue = []


def bot_listening(lock):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('', config.port))
    except:
        print "could not start listener : socket already in use"
        thread.interrupt_main()
        return

    print date_s(time.time())+ " START"
    sock.listen(1)
    sock.settimeout(None)

    # The other side needs to know the server name where the daemon run to open
    # the connection. We write it after bind() because we want to ensure than
    # only one instance of the daemon is running. FIXME: this is not sufficient
    # if the job is migrated so migration is disabled for this daemon.
    servername_filename = os.getenv('HOME') + '/public_html/match_and_split.server'
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
                cmd, title, lang, user = eval(data)
            except:
                print "error", data
                conn.close()
                continue

            t = time.time()
            user = user.replace(' ', '_')
            print user

            if cmd == "status":
                # FIXME: the lock is taken too much time, clone the job queue
                # with the lock taken, then use it
                lock.acquire()
                code = 'utf-8'
                html = '<html>'
                html += '<meta http-equiv="content-type" content="text/html; charset=%s">' % code
                html += '<head></head><body>'

                html += "<html><body>the robot is running.<br/><hr/>"
                html += "<br/>%d jobs in match queue.<br/>"%len(match_queue)
                for i in match_queue:
                    html += date_s(i[3])+' '+i[2]+" "+i[1]+" "+i[0]+"<br/>"
                html += "<br/>%d jobs in split queue.<br/>"%len(split_queue)
                for i in split_queue:
                    mtitle = i[0]
                    mtitle = mtitle.decode('utf-8')
                    codelang = i[1]
                    try:
                        msite = wikipedia.getSite(codelang, config.family)
                        page = wikipedia.Page(msite,mtitle)
                        path = msite.get_address(page.urlname())
                        url = '%s://%s%s' % (msite.protocol(), msite.hostname(), path)
                    except:
                        url = ""
                    html += date_s(i[3])+' '+i[2]+" "+i[1]+" <a href=\""+url+"\">"+i[0]+"</a><br/>"
                html += '</body></html>'
                lock.release()

                conn.send(html)
                conn.close()
                continue

            print date_s(t) + " REQUEST " + user + ' ' + lang + ' ' + cmd + ' ' + title
            if cmd == "match":
                add_job(lock, match_queue, (title, lang, user, t, conn))
            elif cmd == "split":
                add_job(lock, split_queue, (title, lang, user, t, conn))
            else:
                print "error", cmd
                conn.close()

    finally:
        sock.close()
        print "STOP"

        for i in range(len(match_queue)):
            title,lang,user,t,conn = match_queue[i]
            match_queue[i] = (title,lang,user,t,None)
            if conn:
                conn.close()

        for i in range(len(split_queue)):
            title,lang,user,t,conn = split_queue[i]
            split_queue[i] = (title,lang,user,t,None)
            if conn:
                conn.close()

        f = open("wsjobs","w")
        f.write(repr((match_queue, split_queue)))
        f.close()



def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])

# FIXME match_thread() and split_thread() code are identical, except the used
# queue and the function to apply on queue'd item, factorize the code
def match_thread(lock):
    while True:
        title, codelang, user, t, conn = get_job(lock, match_queue)

        time1 = time.time()
        out = ''
        try:
            mysite = wikipedia.getSite(codelang, config.family)
        except:
            print "site error", repr(codelang)
            out = "site error: " + repr(codelang)
            mysite = False
        if mysite:
            wikipedia.setSite(mysite)
            print mysite, title
            title = title.decode('utf-8')
            user = user.decode('utf-8')
            out = do_match(mysite, title, user, codelang)

        if conn:
            conn.send(out)
            conn.close()

        if out and mysite:
            res = " DONE    "
        else:
            res = " FAILED  "

        time2 = time.time()
        print date_s(time2) + res + title.encode('utf-8') + ' ' + user.encode("utf8") + " " + codelang + " (%.2f)"%(time2-time1) + " " + out

        remove_job(lock, match_queue)


def split_thread(lock):
    while True:
        title, codelang, user, t, conn = get_job(lock, split_queue)

        time1 = time.time()
        out = ''
        try:
            mysite = wikipedia.getSite(codelang, config.family)
        except:
            print "site error", repr(codelang)
            out = "site error: " + repr(codelang)
            mysite = False
        if mysite:
            wikipedia.setSite(mysite)
            print mysite, title
            title = title.decode('utf-8')
            user = user.decode('utf-8')
            out = do_split(mysite, title, user, codelang)

        if conn:
            conn.send(out)
            conn.close()

        if out and mysite:
            res = " DONE    "
        else:
            res = " FAILED  "

        time2 = time.time()
        print date_s(time2)+res+user.encode("utf8")+" "+codelang+" (%.2f)"%(time2-time1)+" "+out

        remove_job(lock, split_queue)


if __name__ == "__main__":
    try:
        f = open("wsjobs","r")
        jobs = f.read()
        f.close()
        mq, sq = eval(jobs)
        for i in mq:
            match_queue.append(i)
        for i in sq:
            split_queue.append(i)
    except:
        pass

    lock = thread.allocate_lock()
    thread.start_new_thread(match_thread,(lock,))
    thread.start_new_thread(split_thread,(lock,))
    bot_listening(lock)
