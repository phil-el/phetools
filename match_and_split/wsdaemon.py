
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


# todo : use urllib2


__module_name__ = "wikisourcedaemon"
__module_version__ = "1.0"
__module_description__ = "wikisource daemon"



import sys,os
import socket
import string
import re, Queue
import sre_constants
import thread, time
import simplejson
import urllib2

import align

sys.path.append("../pywikipedia")
import wikipedia, pagegenerators, catlib, pywikibot

mylock = thread.allocate_lock()

page_prefixes={ 'en':'Page', 'fr':'Page', 'de':'Seite', 'it':'Pagina', 'la':'Pagina', 
		'no':'Side', 'es':'P\xc3\xa1gina', 'pt':'P\xc3\xa1gina', 
		'sv':'Sida', 'pl':'Strona', 'hy':'\xd4\xb7\xd5\xbb', 
		'ru':'\xd1\x81\xd1\x82\xd1\x80\xd0\xb0\xd0\xbd\xd0\xb8\xd1\x86\xd0\xb0', 
                'hr':'Stranica', 'hu':'Oldal', 'ca':'P\xc3\xa0gina', 'vi':'Trang', 'sl':'Stran', 'zh':'Page',
                'old':'Page', 'vec':'Pagina' } 



E_ERROR = "error"
E_OK = "ok"

#parameters to pagelist
pl_dict = {}


def get_pl(year,vol):
    global pl_dict
    k = year+","+vol
    pl = pl_dict.get(k)
    if pl != None: return pl
    indexpage = wikipedia.Page(wikipedia.getSite(), "Livre:Revue des Deux Mondes - "+year+" - tome "+vol+".djvu")
    text = indexpage.get()
    m = re.search("<pagelist (.*?)/>",text)
    if m :
	el = m.group(1).split()
        l = []
        for item in el:
            mm = re.match("(\d+)=(\d+)",item)
            if mm: l.append( (int(mm.group(1)) , int(mm.group(2)) ) )
            
	l.sort( lambda x,y: cmp(x[0],y[0]) )
	pl_dict[k] = l
    else:
	pl_dict[k] = {}
    #print pl_dict
    return pl_dict[k]


def repl(m):
    year = m.group(1)
    vol = m.group(2)
    page = int(m.group(3))

    offset = 0 
    pl = get_pl(year,vol)
    for item in pl :
        if page >= item[0]:
            offset = item[0] - item[1]

    return "==[[Page:Revue des Deux Mondes - "+m.group(1)+" - tome "+m.group(2)+".djvu/%d"%( offset + page )+"]]==\n"



def do_match(mysite,maintitle,user,codelang):

    prefix = page_prefixes.get(codelang)
    if not prefix:
	print "no prefix"
	return E_ERROR

    page = wikipedia.Page(mysite,maintitle)
    try:
	text = page.get()
    except:
	print "failed to get page"
	return E_ERROR

    if text.find("{{R2Mondes")!=-1:
	global pl_dict
	pl_dict = {}
	p0 = re.compile("\{\{R2Mondes\|(\d+)\|(\d+)\|(\d+)\}\}\s*\n")
	new_text = p0.sub(repl,text)
	p = re.compile('==\[\[Page:([^=]+)\]\]==\n')
	bl= p.split(new_text)
	for i in range(len(bl)/2):
	    title  = bl[i*2+1]
	    content = bl[i*2+2]
	    filename, pagenum = title.split('/')
	    filename = align.get_djvu(mysite,filename)
	    if not filename:
		return "Erreur : fichier absent"
	    if content.find("R2Mondes")!=-1:
	        p0 = re.compile("\{\{R2Mondes\|\d+\|\d+\|(\d+)\}\}\s*\n")
		bl0 = p0.split(text)
		title0 = bl0[i*2+1].encode("utf8")
		return "Erreur : Syntaxe 'R2Mondes' incorrecte, dans la page "+title0
	    r = align.match_page(content, filename, int(pagenum))
	    print "%s %s  : %f"%(filename, pagenum, r)
	    if r<0.1:
	        p0 = re.compile("\{\{R2Mondes\|\d+\|\d+\|(\d+)\}\}\s*\n")
		bl0 = p0.split(text)
		title0 = bl0[i*2+1].encode("utf8")
		return "Erreur : Le texte ne correspond pas, page %s"%title0
	#the page is ok
        safe_put(page,new_text,user+": match")
	lock.acquire()
	split_queue.insert(0,(maintitle.encode("utf8"),codelang,user.encode("utf8"),time.time(),None))
	lock.release()
	return "ok : transfert en cours."

    prefix = prefix.decode('utf-8')
    p = re.compile("==__MATCH__:\[\["+prefix+":(.*?)/(\d+)\]\]==")
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

    wikipedia.output(djvuname+" "+number)
    try:
        number = int(number)
    except:
	return E_ERROR

    filename = align.get_djvu(mysite,djvuname,True)
    if not filename: return E_ERROR

    output, status = align.do_match(text, filename, djvuname, number, verbose=False, prefix=prefix)
    if status=="ok":
	safe_put(page,head+output,user+": match")
	return E_OK
    else:
        return status

    return E_OK



