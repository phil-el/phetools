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
    # text = text.replace('\\r', '\r')
    text = text.replace('\\n', '\n')
    text = text.replace('\\"', '"')
    text = text.replace('\\\\', '\\')
    text = text.replace('\\037', '\n')
    text = text.replace('\\035', '')
    text = text.replace('\\013', '')
    text = text.rstrip('\n')
    return text


def extract_pdf_text(filename):
    # t_pdftotext = textract.parsers.process(filename, method='pdftotext', encoding='utf-8').decode(encoding='utf-8')
    pipe = subprocess.Popen(['pdftotext', filename, '-'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)  # '-layout' not needed
    text, errors = pipe.communicate()
    text = text.decode(encoding='utf-8', errors='replace')
    text_pages = text.split('\f')
    text_pages = [unquote_text_from_djvu(t) for t in text_pages]
    return text_pages


def extract_djvu_text(filename):
    print("extracting text layer")

    # GTK app are very touchy
    os.environ['LANG'] = 'en_US.UTF8'
    # FIXME: check return code
    ls = subprocess.Popen(['djvutxt', filename, '--detail=page'], stdout=subprocess.PIPE, close_fds=True)
    text = ls.stdout.read()
    ls.wait()

    text_pages = []
    for m in re.finditer(rb'\((page -?\d+ -?\d+ -?\d+ -?\d+[ \n]+"(.*)"[ ]*|)\)\n', text):
        t = m.group(2).decode('utf-8', errors='replace') if m.group(2) else ''  # '' if the page is empty
        t = unquote_text_from_djvu(t)
        text_pages.append(t)
    return text_pages


def ret_val(error, text):
    if error:
        print(f"Error: {error}, {text}")
    return {'error': error, 'text': text}


E_ERROR = 1
E_OK = 0


def do_match(target, cached_text, djvuname, number, verbose, prefix, step):
    """ returns result, status"""

    s = difflib.SequenceMatcher()
    offset = 0
    output = ""
    is_poem = False

    try:
        last_page = cached_text[number - (step + 1) // 2]
    except:
        return ret_val(E_ERROR, "Unable to retrieve text layer for page: " + number)

    for pagenum in range(number, min(number + 1000, len(cached_text)), step):

        if pagenum - number == 10 and offset == 0:
            return ret_val(E_ERROR, "error : could not find a text layer.")

        page1 = last_page
        last_page = page2 = cached_text[pagenum + (step // 2)]

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
        m = re.match(r"(?ms).*(\n\n.*)$", no_color)
        if m and len(m.group(1)) <= 16:
            no_color = no_color[:m.start(1)]
        else:
            m = re.match(r"(?ms).*(\n\w+\W*)$", no_color)
            if m:
                no_color = no_color[:m.start(1) + 1]
        # todo: TO FIX: The first line of the page text is mistakenly placing on the previous page.
        #  Because of this, have to manually move each the page border tags in the resulting text.

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
    """
    If there is already the text of the file in the cache, then use it.
    Otherwise, download the file and extract the text into the cache.
    If `check_timestamp` then check SHA1 of the latest version of the file and download only if it is different.

    Return: text_pages: list, or None
    """

    print("get_djvu", djvuname)

    djvuname = djvuname.replace(" ", "_")
    cache_filename = djvuname + '.dat'

    obj = cache.get(cache_filename)
    if obj:
        cache_sha1, text_pages = obj
        if not check_timestamp:
            return text_pages
    else:
        print("CACHE MISS")

    filepage = copy_File.get_filepage(mysite, djvuname)
    if not filepage:
        # can occur if File: has been deleted
        return None
    sha1 = filepage.latest_file_info.sha1

    if obj and check_timestamp:
        if sha1 == cache_sha1:
            return text_pages
        print("OUTDATED FILE")

    # Download the file, extract text and update cache, remove the file
    try:
        url = filepage.get_file_url()
        utils.copy_file_from_url(url, djvuname, sha1)
        # Recognizing PDF by the file extension. It may be better to determine the type of file by its content.
        text_pages = extract_pdf_text(djvuname) if djvuname.endswith('.pdf') else extract_djvu_text(djvuname)  # '.djvu'
        os.remove(djvuname)
        if text_pages:
            cache.set(cache_filename, (sha1, text_pages))
            return text_pages
    except:
        utils.print_traceback("extract_djvu_text() fail")
