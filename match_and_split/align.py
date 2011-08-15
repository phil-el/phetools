#!/usr/bin/python
# text alignment program
# author : thomasv1 at gmx dot de
# licence : GPL

# FIXME: do the match in unicode, it'll more accurate this way

import match_and_split_config as config

import os, re, time, random
import difflib
import wikipedia

def match_page(target, filename, pagenum):
    s = difflib.SequenceMatcher()
    cmd = config.djvutxtpath + " --page=%d \"%s\" "%(pagenum,filename)
    p = os.popen(cmd.encode("utf8"))
    text1 = p.read()
    p.close()
    text2 = target
    p = re.compile(r'[\W]+')
    text1 = p.split(text1)
    text2 = p.split(text2)
    s.set_seqs(text1,text2)
    ratio = s.ratio()
    return ratio

# returns result, status
def do_match(target, filename, djvuname, number, verbose, prefix):
    s = difflib.SequenceMatcher()
    offset = 0
    output = ""
    is_poem = False

    for i in range(1000):

        if i == 10 and offset == 0:
            return ("", "error : could not find a text layer.")

        pagenum = i + number
        c = config.djvutxtpath + " --page=%d \"%s\" " % (pagenum, filename)
        p = os.popen(c.encode("utf8"))
        page1 = p.read()
        p.close()
        c = config.djvutxtpath +" --page=%d \"%s\" " %((pagenum+1), filename)
        p = os.popen(c.encode("utf8"))
        page2 = p.read()
        p.close()

        text1 = page1+page2
        text2 = target[offset:offset+ int(1.5*len(text1))]

        p = re.compile(r'[\W]+')
        fp = re.compile(r'([\W]+)')
        ftext1 = fp.split(text1)
        ftext2 = fp.split(text2)

        page1 = p.split(page1)
        text1 = p.split(text1)
        text2 = p.split(text2)
        s.set_seqs(text1,text2)

        mb = s.get_matching_blocks()

        try:
            ccc = mb[-2]
            dummy = mb[-1]
        except:
            print "not enough matching blocks"
            break

        ratio = s.ratio()
        #print i, ccc, ratio

        if ratio < 0.1:
            print "low ratio", low_ratio
            break

        mstr = ""
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
                if matched : ss ="\033[1;32m%s\033[0;49m"%ss
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
                    ss ="\033[1;31m%s\033[0;49m"%ss
                if 2*i+1 < len(ftext2):
                    mstr = mstr + ss + ftext2[2*i+1]
                    no_color = no_color + ftext2[2*i] + ftext2[2*i+1]
        if verbose:
            wikipedia.output(mstr)
            print "===================================="

        if is_poem:
            sep = "\n</poem>\n==[["+prefix+":%s/%d]]==\n<poem>\n"%(djvuname,pagenum)
        else:
            sep = "\n==[["+prefix+":%s/%d]]==\n"%(djvuname,pagenum)

        if is_poem:
            no_color = no_color.rstrip()
            if no_color[-3:] == u"\n\n\xab":
                no_color = no_color[:-3]
        else:
            no_color = no_color.rstrip('\n')
            if no_color[-4:] == "\n\n- ":
                no_color = no_color[:-4]
            if no_color[-3:] == "\n\n\"":
                no_color = no_color[:-3]
            if no_color[-5:] == "\n\nIl ":
                no_color = no_color[:-5]
            if no_color[-4:] == u"\n\n\u2013 ":
                no_color = no_color[:-4]
            if no_color[-4:] == u"\n\n\u2014 ":
                no_color = no_color[:-4]
            if no_color[-4:] == u"\n\n\xab ":
                no_color = no_color[:-4]
            if no_color[-5:] == u"\n\n== ":
                no_color = no_color[:-5]

        offset = offset + len(no_color)

        if no_color and no_color[0]=='\n':
            no_color = no_color[1:]
        output = output + sep + no_color

        #update is_poem
        if no_color.find("<poem>") > no_color.find("</poem>"):
            is_poem = True

        if no_color.find("<poem>") < no_color.find("</poem>"):
            is_poem = False

    if offset != 0 and target[offset:]:
        output = output+"\n=== no match ===\n" + target[offset:]

    if offset == 0:
        output = ""

    if output == "":
        return ("", "text does not match")
    else:
        return (output, "ok")


# FIXME: use urllib2 instead of wget
# FIXME: theorically it's possible to get a name collision if two different
# wiki have local file with same name but different contents.
def get_djvu(mysite, djvuname, check_timestamp = False):
    print "get_djvu", repr(djvuname)

    djvuname = djvuname.replace(" ","_")
    filename = "djvu/" + djvuname
    if not os.path.exists(filename):
        # FIXME: use a LRU rather to randomly delete a file in the cache, the
        # best way is to save in the cache only the text layer, but extracting
        # the whole text layer isn't too costly for big volume?
        o = os.listdir("djvu")
        if len(o) > 19:
            k = random.randint(0, len(o) - 1)
            print "deleting " + o[k]
            os.unlink("djvu/" + o[k])

        filepage = wikipedia.ImagePage(mysite, "File:" + djvuname)
        try:
            url = filepage.fileUrl()
        except:
            return False

        wikipedia.output("getting " + djvuname)
        cmd = 'wget -q -O "%s" %s'%(filename, url)
        os.system(cmd.encode("utf8"))
    else:
        if check_timestamp:
            (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(filename)
            filepage = wikipedia.ImagePage(mysite,"File:"+djvuname)
            hist = filepage.getFileVersionHistory()
            date = hist[0][0]
            timestamp = time.mktime( time.strptime(date, "%Y-%m-%dT%H:%M:%SZ") )
            if timestamp - mtime > 120: #allow 2 minutes difference
                print "OUTDATED FILE", timestamp, mtime , ":", timestamp - mtime
                try:
                    url = filepage.fileUrl()
                except:
                    return filename
                os.unlink(filename)
                wikipedia.output("getting "+djvuname)
                cmd = 'wget -q -O "%s" %s'%(filename,url)
                os.system(cmd.encode("utf8"))

    return filename
