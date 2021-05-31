# text alignment program
# author : thomasv1 at gmx dot de
# author : phe at some dot where
# licence : GPL

import os, re
import difflib
import pywikibot
from common import utils
from common import copy_File
import subprocess


def match_page(target, source):
    s = difflib.SequenceMatcher()
    text1 = source
    text2 = target
    p = re.compile(r'[\W]+')
    text1 = p.split(text1)
    text2 = p.split(text2)
    s.set_seqs(text1, text2)
    ratio = s.ratio()
    return ratio


def unquote_text_from_djvu(text):
    #text = text.replace('\\r', '\r')
    text = text.replace('\\n', '\n')
    text = text.replace('\\"', '"')
    text = text.replace('\\\\', '\\')
    text = text.replace('\\037', '\n')
    text = text.replace('\\035', '')
    text = text.replace('\\013', '')
    text = text.rstrip('\n')
    return text


def extract_djvu_text(url, filename, sha1):
    print("extracting text layer")

    if type(filename) == type(''):
        filename = filename.encode('utf-8')

    utils.copy_file_from_url(url, filename, sha1)

    data = []
    # GTK app are very touchy
    os.environ['LANG'] = 'en_US.UTF8'
    # FIXME: check return code
    ls = subprocess.Popen(['djvutxt', filename, '--detail=page'], stdout=subprocess.PIPE, close_fds=True)
    text = ls.stdout.read()
    ls.wait()
    for t in re.finditer(r'\((page -?\d+ -?\d+ -?\d+ -?\d+[ \n]+"(.*)"[ ]*|)\)\n', text):
        t = unicode(t.group(1), 'utf-8', 'replace')
        t = re.sub(r'^page \d+ \d+ \d+ \d+[ \n]+"', '', t)
        t = re.sub('"[ ]*$', '', t)
        t = unquote_text_from_djvu(t)
        data.append(t)

    os.remove(filename)

    return sha1, data


def ret_val(error, text):
    if error:
        print(f"Error: {error}, {text}")
    return {'error': error, 'text': text}


E_ERROR = 1
E_OK = 0


# returns result, status
def do_match(target, cached_text, djvuname, number, verbose, prefix, step):
    s = difflib.SequenceMatcher()
    offset = 0
    output = ""
    is_poem = False

    try:
        last_page = cached_text[number - (step+1)//2]
    except:
        return ret_val(E_ERROR, "Unable to retrieve text layer for page: " + number)

    for pagenum in range(number, min(number + 1000, len(cached_text)), step):

        if pagenum - number == 10 and offset == 0:
            return ret_val(E_ERROR, "error : could not find a text layer.")

        page1 = last_page
        last_page = page2 = cached_text[pagenum + (step//2)]

        text1 = page1 + page2
        text2 = target[offset:offset + int(1.5 * len(text1))]

        p = re.compile(r'[\W]+', re.U)
        fp = re.compile(r'([\W]+)', re.U)
        ftext1 = fp.split(text1)
        ftext2 = fp.split(text2)

        page1 = p.split(page1)
        text1 = p.split(text1)
        text2 = p.split(text2)
        s.set_seqs(text1, text2)

        mb = s.get_matching_blocks()
        if len(mb) < 2:
            print("LEN(MB) < 2, breaking")
            break
        ccc = mb[-2]
        # no idea what was the purpose of this
        # dummy = mb[-1]
        ratio = s.ratio()
        # print(i, ccc, ratio)

        if ratio < 0.1:
            print("low ratio", ratio)
            break
        mstr = ''
        overflow = False
        for i in range(ccc[0] + ccc[2]):
            matched = False
            for m in mb:
                if i >= m[0] and i < m[0] + m[2]:
                    matched = True
                    if i >= len(page1):
                        overflow = True
                    break
            if not overflow:
                ss = ftext1[2 * i]
                if matched:
                    ss = "\033[1;32m%s\033[0;49m" % ss
                if 2 * i + 1 < len(ftext1):
                    mstr = mstr + ss + ftext1[2 * i + 1]
        if verbose:
            pywikibot.output(mstr)
            print("--------------------------------")

        mstr = ""
        no_color = ""
        overflow = False
        for i in range(ccc[1] + ccc[2]):
            matched = False
            for m in mb:
                if i >= m[1] and i < m[1] + m[2]:
                    matched = True
                    if m[0] + i - m[1] >= len(page1):
                        overflow = True
                    break

            if not overflow:
                ss = ftext2[2 * i]
                if matched:
                    ss = "\033[1;31m%s\033[0;49m" % ss
                if 2 * i + 1 < len(ftext2):
                    mstr = mstr + ss + ftext2[2 * i + 1]
                    no_color = no_color + ftext2[2 * i] + ftext2[2 * i + 1]
        if verbose:
            pywikibot.output(mstr)
            print("====================================")

        sep = f"\n==[[{prefix}:{djvuname}/{pagenum}]]==\n"
        if is_poem:
            sep = f"\n</poem>{sep}<poem>\n"

        # Move the end of the last page to the start of the next page
        # if the end of the last page look like a paragraph start. 16 char
        # width to detect that is a guessed value.
        no_color = no_color.rstrip()
        match = re.match(r"(?ms).*(\n\n.*)$", no_color)
        if match and len(match.group(1)) <= 16:
            no_color = no_color[:-len(match.group(1))]
        else:
            match = re.match(r"(?ms).*(\n\w+\W*)$", no_color)
            if match:
                no_color = no_color[:-(len(match.group(1)) - 1)]

        offset += len(no_color)

        if no_color and no_color[0] == '\n':
            no_color = no_color[1:]
        no_color = no_color.lstrip(' ')
        output += sep + no_color

        if no_color.rfind("<poem>") > no_color.rfind("</poem>"):
            is_poem = True
        elif no_color.rfind("<poem>") < no_color.rfind("</poem>"):
            is_poem = False

    if offset != 0 and target[offset:]:
        if len(target) - offset >= 16:
            output += "\n=== no match ===\n"
        output += target[offset:].lstrip(' ')

    if offset == 0:
        output = ""

    if output == "":
        return ret_val(E_ERROR, "text does not match")
    else:
        return ret_val(E_OK, output)


# It's possible to get a name collision if two different wiki have local
# file with the same name but different contents. In this case the cache will
# be ineffective but no wrong data can be used as we check its sha1.
def get_djvu(cache, mysite, djvuname, check_timestamp=False):
    print("get_djvu", djvuname)

    djvuname = djvuname.replace(" ", "_")
    cache_filename = djvuname + '.dat'

    obj = cache.get(cache_filename)
    if not obj:
        print("CACHE MISS")
        filepage = copy_File.get_filepage(mysite, djvuname)
        if not filepage:
            # can occur if File: has been deleted
            return None
        try:
            url = filepage.fileUrl()
            obj = extract_djvu_text(url, djvuname, filepage.getFileSHA1Sum())
        except:
            utils.print_traceback("extract_djvu_text() fail")
            obj = None
        if obj:
            cache.set(cache_filename, obj)
        else:
            return None
    else:
        if check_timestamp:
            filepage = copy_File.get_filepage(mysite, djvuname)
            if not filepage:
                # can occur if File: has been deleted
                return None
            sha1 = filepage.getFileSHA1Sum()
            if sha1 != obj[0]:
                print("OUTDATED FILE")
                url = filepage.fileUrl()
                try:
                    obj = extract_djvu_text(url, djvuname, sha1)
                    cache.set(cache_filename, obj)
                except:
                    return None

    return obj[1]
