# -*- coding: utf-8 -*-
# text alignment program
# author : thomasv1 at gmx dot de
# author : phe at some dot where
# licence : GPL

import os, re, random
import pickle
import difflib
import wikipedia
import urllib

def url_opener():
    opener = urllib.URLopener()
    opener.addheaders = [('User-agent', 'MW_match_and_split')]
    return opener

def copy_file_from_url(url, out_file):
    opener = url_opener()
    fd_in = opener.open(url)
    fd_out = open(out_file, "wb")
    data = True
    while data:
        data = fd_in.read(4096)
        if data:
            fd_out.write(data)
    fd_in.close()
    fd_out.close()

def data_filename(filename):
    return filename[:-4] + "dat"

pickle_obj = None
pickle_filename = None
def get_pickle_obj(filename):
    global pickle_obj, pickle_filename
    if pickle_filename != filename:
        print "Mem cache miss for:", filename.encode(u'utf-8')
        fd = open(data_filename(filename), "rb")
        pickle_obj = pickle.load(fd)
        fd.close()
        pickle_filename = filename
    return pickle_obj

def read_djvu_page(filename, pagenum):
    obj = get_pickle_obj(filename)
    if pagenum > 0 and pagenum <= len(obj[1]):
        return obj[1][pagenum-1]
    else:
        return u""

def get_nr_djvu_pages(filename):
    obj = get_pickle_obj(filename)
    return len(obj[1])

def match_page(target, filename, pagenum):
    s = difflib.SequenceMatcher()
    text1 = read_djvu_page(filename, pagenum)
    text2 = target
    p = re.compile(ur'[\W]+')
    text1 = p.split(text1)
    text2 = p.split(text2)
    s.set_seqs(text1,text2)
    ratio = s.ratio()
    return ratio

def unquote_text_from_djvu(text):
    #text = text.replace(u'\\r', u'\r')
    text = text.replace(u'\\n', u'\n')
    text = text.replace(u'\\"', u'"')
    text = text.replace(u'\\\\', u'\\')
    text = text.replace(u'\\037', u'\n')
    text = text.replace(u'\\035', u'')
    text = text.replace(u'\\013', u'')
    text = text.rstrip(u'\n')
    return text

def quote_filename(filename):
    result = u''
    for ch in filename:
        if ch in u";&|><*?`$(){}[]!#'\"":
            result += u"\\"
        result += ch
    return result

def extract_djvu_text(url, filename, sha1):
    copy_file_from_url(url, filename)
    data = []
    cmdline = "/home/phe/bin/djvutxt -detail=page %s" % quote_filename(filename).encode('utf-8')
    print cmdline
    fd = os.popen(cmdline)
    text = fd.read()
    for t in re.finditer(u'\((page -?\d+ -?\d+ -?\d+ -?\d+[ \n]+"(.*)"[ ]*|)\)\n', text):
        t = unicode(t.group(1), 'utf-8', 'replace')
        t = re.sub(u'^page \d+ \d+ \d+ \d+[ \n]+"', u'', t)
        t = re.sub(u'"[ ]*$', u'', t)
        t = unquote_text_from_djvu(t)
        data.append(t)
    fd.close()
    os.remove(filename)
    fd = open(data_filename(filename), "wb")
    pickle.dump((sha1, data), fd)
    fd.close()
    global pickle_obj, pickle_filename
    pickle_filename = filename
    pickle_obj = (sha1, data)

def ret_val(error, text):
    if error:
        print "Error: %d, %s" % (error, text)
    return  { 'error' : error, 'text' : text }

E_ERROR = 1
E_OK = 0

# returns result, status
def do_match(target, filename, djvuname, number, verbose, prefix):
    s = difflib.SequenceMatcher()
    offset = 0
    output = ""
    is_poem = False

    max_pages = get_nr_djvu_pages(filename)
    last_page = read_djvu_page(filename, number)

    for pagenum in range(number, min(number + 1000, max_pages)):

        if pagenum - number == 10 and offset == 0:
            return ret_val(E_ERROR, "error : could not find a text layer.")

        page1 = last_page
        last_page = page2 = read_djvu_page(filename, pagenum + 1)

        text1 = page1+page2
        text2 = target[offset:offset+ int(1.5*len(text1))]

        p = re.compile(ur'[\W]+', re.U)
        fp = re.compile(ur'([\W]+)', re.U)
        ftext1 = fp.split(text1)
        ftext2 = fp.split(text2)

        page1 = p.split(page1)
        text1 = p.split(text1)
        text2 = p.split(text2)
        s.set_seqs(text1,text2)

        mb = s.get_matching_blocks()
        if len(mb) < 2:
            print "LEN(MB) < 2, breaking"
            break
        ccc = mb[-2]
        dummy = mb[-1]
        ratio = s.ratio()
        #print i, ccc, ratio

        if ratio < 0.1:
            print "low ratio", ratio
            break
        mstr = u""
        overflow = False
        for i in range(ccc[0] + ccc[2]):
            matched = False
            for m in mb:
                if i >= m[0] and i < m[0]+m[2] :
                   matched = True
                   if i >= len(page1):
                       overflow = True
                   break
            if not overflow:
                ss = ftext1[2*i]
                if matched:
                    ss =u"\033[1;32m%s\033[0;49m"%ss
                if 2*i+1 < len(ftext1):
                    mstr = mstr + ss + ftext1[2*i+1]
        if verbose:
            wikipedia.output(mstr)
            print "--------------------------------"

        mstr = ""
        no_color = ""
        overflow = False
        for i in range(ccc[1]+ccc[2]):
            matched = False
            for m in mb:
                if i >= m[1] and i < m[1]+m[2] :
                   matched = True
                   if m[0]+i-m[1] >= len(page1):
                       overflow = True
                   break

            if not overflow:
                ss = ftext2[2*i]
                if matched:
                    ss =u"\033[1;31m%s\033[0;49m"%ss
                if 2*i+1 < len(ftext2):
                    mstr = mstr + ss + ftext2[2*i+1]
                    no_color = no_color + ftext2[2*i] + ftext2[2*i+1]
        if verbose:
            wikipedia.output(mstr)
            print "===================================="

        if is_poem:
            sep = u"\n</poem>\n==[["+prefix+":%s/%d]]==\n<poem>\n"%(djvuname,pagenum)
        else:
            sep = u"\n==[["+prefix+":%s/%d]]==\n"%(djvuname,pagenum)

        # Move the end of the last page to the start of the next page
        # if the end of the last page look like a paragraph start. 16 char
        # width to detect that is a guessed value.
        no_color = no_color.rstrip()
        match = re.match(u"(?ms).*(\n\n.*)$", no_color)
        if match and len(match.group(1)) <= 16:
            no_color = no_color[:-len(match.group(1))]
        else:
            match = re.match(u"(?ms).*(\n\w+\W*)$", no_color)
            if match:
                no_color = no_color[:-(len(match.group(1)) - 1)]

        offset += len(no_color)

        if no_color and no_color[0]==u'\n':
            no_color = no_color[1:]
        no_color = no_color.lstrip(u' ')
        output += sep + no_color

        if no_color.rfind(u"<poem>") > no_color.rfind(u"</poem>"):
            is_poem = True
        elif no_color.rfind(u"<poem>") < no_color.rfind(u"</poem>"):
            is_poem = False

    if offset != 0 and target[offset:]:
        if len(target) - offset >= 16:
            output += u"\n=== no match ===\n"
        output += target[offset:].lstrip(u' ')

    if offset == 0:
        output = ""

    if output == "":
        return ret_val(E_ERROR, "text does not match")
    else:
        return ret_val(E_OK, output)

def get_filepage(site, djvuname):
    filepage = wikipedia.ImagePage(site, "File:" + djvuname)
    # required to get the SHA1 when the file is on commons.
    if filepage.fileIsOnCommons():
        site = wikipedia.getSite(code = 'commons', fam = 'commons')
        filepage = wikipedia.ImagePage(site, "File:" + djvuname)
    return filepage

# It's possible to get a name collision if two different wiki have local
# file with the same name but different contents. In this case the cache will
# be ineffective but no wrong data can be used as we check its sha1.
def get_djvu(mysite, djvuname, check_timestamp = False):
    print "get_djvu", repr(djvuname)

    djvuname = djvuname.replace(" ", "_")
    filename = "/home/phe/wsbot/cache/djvu/" + djvuname
    if not os.path.exists(data_filename(filename)):
        # FIXME: use a LRU rather to randomly delete a file in the cache.
        print "CACHE MISS"
        o = os.listdir("/home/phe/wsbot/cache/djvu")
        if len(o) >= 32:
            k = random.randint(0, len(o) - 1)
            print "deleting " + o[k]
            os.unlink("/home/phe/wsbot/cache/djvu/" + o[k])

        try:
            filepage = get_filepage(mysite, djvuname)
            url = filepage.fileUrl()
        except:
            return False

        print "extracting text layer"
        extract_djvu_text(url, filename, filepage.getHash())
    else:
        if check_timestamp:
            try:
                filepage = get_filepage(mysite, djvuname)
            except: # can occur if file has been deleted.
                return False
            obj = get_pickle_obj(filename)
            if obj[0] != filepage.getHash():
                print "OUTDATED FILE", obj[0], filepage.getHash()
                try:
                    url = filepage.fileUrl()
                except:
                    return filename
                print "extracting text layer"
                extract_djvu_text(url, filename, filepage.getHash())

    return filename
