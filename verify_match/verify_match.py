# -*- coding: utf-8 -*-
# GPL V2, author phe

import sys
# FIXME: is there a better way to do this?
sys.path.append('/data/project/phetools/phe/common')
sys.path.append('/data/project/phetools/phe/match_and_split')
sys.path.append('/data/project/phetools/wikisource')

from ws_namespaces import page as page_prefixes, index as index_prefixes

import lifo_cache
import re
import tempfile
import os
import ws_utils
import utils
import pywikibot
from pywikibot import pagegenerators as pagegen

def is_imported_page(text):
    if re.search(u'{{[iI]wpage[ ]*\|[^}]+}}', text):
        return True
    return False

def load_pages(book_name, opt, cache):
    # It's more efficient to do two pass, in the first we don't preload
    # contents but only check if the cache is ok.
    remaining_pages = []
    pages = []
    page_ns_name = page_prefixes['wikisource'][opt.lang]
    page_name = page_ns_name + u':' + book_name + u'/'
    gen = pagegen.PrefixingPageGenerator(page_name, site = opt.site)
    for p in gen:
        page_nr = int(re.match(u'.*/(\d+)$', p.title()).group(1))
        if not cache.has_key(page_nr) or cache[page_nr][0] != p.latestRevision():
            remaining_pages.append(p)
        else:
            pages.append( ( None, page_nr, p.latestRevision() ) )

    # and in the second pass we preload contents for cache miss,
    # imported pages are never cached, but that's not a no big deal
    for p in pagegen.PreloadingGenerator(remaining_pages):
        text = p.get()
        if not is_imported_page(text):
            page_nr = int(re.match(u'.*/(\d+)$', p.title()).group(1))
            pages.append( ( text, page_nr, p.latestRevision() ) )

    return pages

# FIXME: share
def strip_link(matchobj):
    link = matchobj.group(1)
    # break image with legend, it doesn't look like sensible to use this
    # in a section title
    if link.startswith(u'Image:') or link.startswith(u'image:'):
        return u''
    link = link.split('|')
    link = link[-1]
    return link

def remove_template_pass(text):
    text = re.sub(u'{{…\|[^}]*}}', u'', text)
    text = re.sub(u'{{[fF]ormatnum:([^{}]*?)}}', u'\\1', text)
    text = re.sub(u'{{[tT]iret\|([^{}]*?)\|[^{}]*?}}', u'\\1-', text)
    text = re.sub(u'{{[sS]éparateur}}', u'', text)
    text = re.sub(u'{{[sS]éparateur de points(\|[^{}]*)?}}', u'', text)
    text = re.sub(u'{{[sS]p\|([^{}|]*)}}', u'\\1', text)
    text = re.sub(u'{{[sS]\|([^{}|]*)}}', u'\\1e siècle', text)
    text = re.sub(u'{{[sS]\|([^{}|]*)\|e}}', u'\\1e siècle', text)
    text = re.sub(u'{{[sS]\|([^{}|]*)\|er}}', u'\\1er siècle', text)
    text = re.sub(u'{{[sS]\|([^{}|]*)\|([^{}|]*)\|s}}', u'\\1\\2 siècles', text)
    text = re.sub(u'{{[sS]\|([^{}|]*)\|([^{}|]*)\|-}}', u'\\1\\2', text)
    text = re.sub(u'{{[sS]p\|[^{}]*\|([^{}]*)}}', u'\\1', text)
    text = re.sub(u'{{[aA]ngle\|([^{}]*)\|([^{}]*)\|([^{}]*)\|([^{}]*)}}', u'\\1 \\2 \\3 \\4', text)
    text = re.sub(u'{{[aA]ngle\|([^{}]*)\|([^{}]*)\|([^{}]*)}}', u'\\1 \\2 \\3', text)
    text = re.sub(u'{{[aA]ngle\|([^{}]*)\|([^{}]*)}}', u'\\1 \\2 ', text)
    text = re.sub(u'{{[Ii]nitiale\|([^{}|]*(\|[^{}]*)*)}}', u'\\1', text)
    text = re.sub(u'{{[sS]éparateur\|[^{}]*}}', u'', text)
    text = re.sub(u'{{[aA]\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[aA]linéa\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[fF]AD\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[fF]lotteADroite\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[aA]linéa\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[dD]\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[dD]roite\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[tT]iret2\|[^{}]*?\|([^{}]*?)}}', u'\\1', text)
    text = re.sub(u'{{[Ll]ang\|[^{}]*?\|([^{}]*?)}}', u'\\1', text)
    text = re.sub(u'{{[tT]aille\|([^{}]*?)\|[^{}]*?}}', u'\\1', text)
    text = re.sub(u'{{[tT]\|([^{}]*?)\|[^{}]*?}}', u'\\1', text)
    text = re.sub(u'{{[Cc]orr\|([^{}]*?)\|[^{}]*?}}', u'\\1', text)
    text = re.sub(u'{{[eE]\|([^{}]*?)}}', u'\\1', text)
    text = re.sub(u'{{[eE]}}', u'e', text)
    text = re.sub(u'{{[Cc]itation\|([^{}]*?)}}', u'\\1', text)
    text = re.sub(u'{{[Cc]aché\|[^{}]*?}}', u'', text)
    text = re.sub(u'(?ms){{([Cc]|[Cc]entré)\|([^{}]*?)(\|[^{}]*)*}}', u'\\2', text)
    text = re.sub(u'{{[PpSs]c\|([^{}]*?)}}', u'\\1', text)
    text = re.sub(u'{{[tT][234]\|([^{}]*?)(\|(fs|sp|lh|align)[ ]*=[ ]*[^}]*)*}}', u'\\1', text)  
    text = re.sub(u'{{[tT][234]\|([^{}]*?)\|([^{}]*?)(\|(fs|sp|lh|align)[ ]*=[ ]*[^}]*)*}}', u'\\2 \\1', text)
    text = re.sub(u'{{[tT][234]\|([^{}|]*?)}}', u'\\1', text)
    text = re.sub(u'{{[tT][234]\|([^{}]*?)\|([^{}]*?)}}', u'\\2 \\1', text)
    text = re.sub(u'{{[tT][1234]mp\|([^{}|]*?)}}', u'\\1', text)
    text = re.sub(u'{{[lL]ettrine\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[Rr]efa\|([^{}|]*)\|([^{}]*)}}', u'\\2', text)
    text = re.sub(u'{{[Rr]efa\|([^{}|]*)}}', u'\\1', text)
    text = re.sub(u'{{[Rr]efl\|([^{}]*)\|num=([^{}]*)}}', u'\\2', text)
    text = re.sub(u'{{[Rr]efl\|([^{}|]*)\|nosup}}', u'\\1', text)
    text = re.sub(u'{{[Rr]efl\|([^{}|]*)}}', u'\\1', text)
    text = re.sub(u'{{[Pp]li\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{-[-]+(\|[^{}]*)*}}', u'', text)
    text = re.sub(u'{{[Bb]rn\|[^{}]*}}', u'', text)
    text = re.sub(u'{{[Pp]ersonnage\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[Pp]ersonnageD\|([^{}|]*)\|[^|{}]*\|([^|{}]*)(\|[^{}]*)*}}', u'\\1 \\2', text)
    text = re.sub(u'{{[Dd]idascalie\|([^{}|]*)(\|[^{}]*)*}}', u'\\1', text)
    text = re.sub(u'{{[Aa]stérisme(\|[^{}]*)*}}', u'', text)
    text = re.sub(u'{{[Aa]stérisque(\|[^{}]*)*}}', u'', text)
    text = re.sub(u'{{[Pp]etitTitre\|([^{}|]*)}}', u'\\1', text)
    text = re.sub(u'{{[Pp]etitTitre2\|([^{}|]*)}}', u'\\1', text)
    text = re.sub(u'(?ms){{[Éé]pigraphe\|([^{}|]*)}}', u'\\1', text)
    text = re.sub(u'(?ms){{[Éé]pigraphe\|([^{}]*?)\|([^{}]*?)}}', u'\\1 \\2', text)
    text = re.sub(u'{{—[ ]*\|([^{}]*)}}', u'', text)
    text = re.sub(u'{{\.\.\.|([^{}]*)}}', u'', text)

    return text

def remove_template(text):
    old_text = None
    while old_text != text:
        old_text = text
        text = remove_template_pass(text)
    return text

def remove_ocr_template_pass(text):
    text = re.sub(u'{{[Ss]c\|([^{}]*?)}}', u'\\1', text)
    return text

def remove_ocr_template(text):
    old_text = None
    while old_text != text:
        old_text = text
        text = remove_ocr_template_pass(text)
    return text

def remove_tag_pass(text):
    text = re.sub(u'(?msi)<div[^>]*?>(.*?)</div>', u'\\1', text)
    text = re.sub(u'(?msi)<sup[^>]*?>(.*?)</sup>', u'\\1', text)
    text = re.sub(u'(?msi)<includeonly[^>]*?>(.*?)</includeonly>', u'', text)
    text = re.sub(u'(?msi)<span[^>]*?>(.*?)</span>', u'\\1', text)
    text = re.sub(u'(?msi)<big[^>]*?>(.*?)</big>', u'\\1', text)
    text = re.sub(u'(?msi)<small[^>]*?>(.*?)</small>', u'\\1', text)
    text = re.sub(u'(?msi)<i[^>]*?>(.*?)</i>', u'\\1', text)
    text = re.sub(u'(?msi)<center[^>]*?>(.*?)</center>', u'\\1', text)
    text = re.sub(u'(?msi)<poem[^>]*?>(.*?)</poem>', u'\\1', text)
    return text

def remove_tag(text):
    old_text = None
    while old_text != text:
        old_text = text
        text = remove_tag_pass(text)
    return text

def explode_template_params(text):
    result = {}
    for it in re.finditer(u'([\w]+)[ ]*=[ ]*([^|}]*)', text):
        result[it.group(1)] = it.group(2)
    return result

def handle_table(text):
    tables = []
    for it in re.finditer(u'(?ms){{[tT]able[ ]*\|[^}]*?}}', text):
        tables.append((it.start(0), it.end(0)))
    tables.sort(reverse = True)
    for t in tables:
        result = explode_template_params(text[t[0]:t[1]])
        new_text = u''
        if result.has_key(u'section'):
            new_text += result[u'section'] + u' '
        if result.has_key(u'titre'):
            new_text += result[u'titre'] + u' '
        if result.has_key(u'page'):
            new_text += result[u'page'] + u' '
        text = text[0:t[0]] + u' ' + new_text + text[t[1]:]
    #if len(tables):
    #    print text.encode(u'utf-8')
    return text

def common_transform(text):
    text = text.replace(u'ſ', u's')
    return text

def transform_text(text, opt):
    text = remove_tag(text)
    text = re.sub(u'(?msi)<section[^>]*?/>', u'', text)
    text = re.sub(u'(?msi)<br[^>]*?>', u' ', text)
    text = re.sub(u'(?msi)<nowiki[^>]*?>', u'', text)
    text = re.sub(u'(?msi)</nowiki[^>]*?>', u'', text)
    text = remove_template(text)
    text = re.sub(u'\[\[([^\]]*?)\]\]', strip_link, text)
    text = text.replace(u'__NOTOC__', u'')
    text = re.sub(u'style="[^"]*"', u'', text)
    text = re.sub(u"style='[^']*'", u'', text)
    text = re.sub(u'cellpadding="[0-9]+"', u'', text)
    text = re.sub(u"cellpadding='[0-9]+'", u'', text)
    text = re.sub(u"cellpadding=[0-9]+", u'', text)
    text = re.sub(u'cellspacing="[0-9]+"', u'', text)
    text = re.sub(u"cellspacing='[0-9]+'", u'', text)
    text = re.sub(u"cellspacing=[0-9]+", u'', text)
    text = re.sub(u'rowspan="[0-9]+"', u'', text)
    text = re.sub(u"rowspan='[0-9]+'", u'', text)
    text = re.sub(u"rowspan=[0-9]+", u'', text)
    text = re.sub(u'colspan="[0-9]+"', u'', text)
    text = re.sub(u"colspan='[0-9]+'", u'', text)
    text = re.sub(u"colspan=[0-9]+", u'', text)
    text = re.sub(u'border="[0-9]+"', u'', text)
    text = re.sub(u"border='[0-9]+'", u'', text)
    text = re.sub(u"border=[0-9]+", u'', text)
    text = re.sub(u'align="(left|right|center|justify)"', u'', text)
    text = re.sub(u"align='(left|right|center|justify)'", u'', text)
    text = re.sub(u"align=(left|right|center|justify)", u'', text)
    text = re.sub(u'valign="(top|middle|bottom)"', u'', text)
    text = re.sub(u"valign='(top|middle|bottom)'", u'', text)
    text = re.sub(u"valign=(top|middle|bottom)", u'', text)
    text = re.sub(u'width="[0-9]+(em|px|%)"', u'', text)
    text = re.sub(u"width='[0-9]+(em|px|%)'", u'', text)
    text = re.sub(u"width=[0-9]+(em|px|%)", u'', text)

    text = re.sub(u'__+', u'', text)
    text = text.replace(u'&nbsp;', u' ')

    header, text, footer = ws_utils.split_page_text(text)

    text = re.sub(u'(?msi)<noinclude[^>]*?>(.*?)</noinclude>', u'\\1', text)

    # FIXME: numérotation is center|left|right
    match = re.search(u'{{[Nn](r|umérotation)\|([^}]*)\|([^}]*)\|([^}]*)}}', header)
    if match:
        text = match.group(2) + u' ' + match.group(3) + u' ' + match.group(4) + u' ' + text
    else:
        match = re.search(u'{{[Nn](r|umérotation)\|([^}]*)\|([^}]*)}}', header)
        if match:
            text = match.group(2) + u' ' + match.group(3) + u' ' + text

    # move downward all ref. First ref follow to ensure the right order
    refs = []
    for it in re.finditer(u'(?msi)<ref follow=[^>]*>(.*?)</ref>', text):
        refs.append(it.group(1))
    for it in re.finditer(u'(?msi)<ref( name=[^>]*)*>(.*?)</ref>', text):
        refs.append(it.group(2))
    text = re.sub(u'(?msi)<ref( name=[^>]*)*>.*?</ref>', u'', text)
    for ref in refs:
        text += u'\n' + ref

    text = re.sub(u'(?msi)<ref follow=[^>]*>.*?</ref>', u'', text)

    text = handle_table(text)

    if opt.upper_case:
        text = text.upper()
    return text

def transform_ocr_text(ocr_text, opt):
    ocr_text = remove_ocr_template(ocr_text)
    ocr_text = ocr_text.replace(u'\\037', u'')
    ocr_text = ocr_text.replace(u'\\035', u'')
    ocr_text = ocr_text.replace(u'\\013', u'')
    if opt.upper_case:
        ocr_text = ocr_text.upper()
    return ocr_text

def run_diff(ocr_text, text):
    ocr_text = u"\n".join(ocr_text) + u"\n"
    temp1 = tempfile.NamedTemporaryFile(suffix = '.txt')
    utils.write_file(temp1.name, ocr_text)
    text = u"\n".join(text) + u"\n"
    temp2 = tempfile.NamedTemporaryFile(suffix = '.txt')
    utils.write_file(temp2.name, text)
    cmdline = "diff -U 0 " + temp1.name + " " + temp2.name
    fd = os.popen(cmdline)
    diff = ''
    for t in fd.readlines():
        diff += t
    fd.close()
    return unicode(diff, 'utf-8')

def white_list(left, right):
    lst = {
        u'CLANS' : 'DANS',
        u'CELTE' : u'CETTE',
        u"CLOUTE" : u"DOUTE",
        u"INONDE" : u"MONDE",
        u"CLOUTAIS" : u"DOUTAIS",
        u"GRECLINS" : u"GREDINS",
        u"GRECLIN" : u"GREDIN",
        u"CLOUTER" : u"DOUTER",
        u"CLOUTÂT" : u"DOUTÂT",
        u"CLIGNE" : u"DIGNE",
        u"US" : u"ILS",
        u"CLAMES" : u"DAMES",
        u"CLAME" : u"DAME",
        u"TON" : u"L’ON",
        u"JUE" : u"QUE",
        u"CJUE" : u"QUE",
        u"FDLES" : u"FILLES",
        u"FDLE" : u"FILLE",
        u"H" : u"À",
        u"A" : u"À",
        u"I" : u"",
        u"TÉtat" : u"L’ÉTAT",
        }

    if left in lst and right == lst[left]:
        return True
    return False

def transform_ocr_diff(diff):
    diff = diff.replace(u'OEUVRÉ', u'ŒUVRÉ')
    diff = diff.replace(u'COETERA', u'CÆTERA')
    diff = diff.replace(u'VOEUX', u'VŒUX')
    diff = diff.replace(u'MOEURS', u'MŒURS')
    diff = diff.replace(u'SOEUR', u'SŒUR')
    diff = diff.replace(u'CHOEUR', u'CHŒUR')
    diff = diff.replace(u'NOEUD', u'NŒUD')
    diff = diff.replace(u'VOEUX', u'VŒUX')
    diff = diff.replace(u'COEUR', u'CŒUR')
    diff = diff.replace(u'OEUVRE', u'ŒUVRE')
    diff = diff.replace(u'GOETHE', u'GŒTHE')
    diff = diff.replace(u'HAENDEL', u'HÆNDEL')
    diff = diff.replace(u'OEIL', u'ŒIL')
    diff = diff.replace(u'OEUF', u'ŒUF')
    diff = diff.replace(u'A', u'À')

    return diff

def check_diff(text, opt):
    text = text.split(u'\n')
    left = u''.join([ x[1:] for x in text if len(x) > 1 and x[0] == '-' ])
    right= u''.join([ x[1:] for x in text if len(x) > 1 and x[0] == '+' ])
    #if (re.search(u'DE', right) and re.search(u'À', left)) or (re.search(u'DE', left) and re.search(u'À', right)):
    #    print right
    #    print left
    if len(left) <= 3 and len(right) <= 3:
        if re.search(u'[0-9]', left) or re.search(u'[0-9]', right):
            return False
    if white_list(left.upper(), right.upper()):
        return False
    #print left.encode('utf-8')
    #print right.encode('utf-8')
    return True

def has_nr_template(text):
    match = re.search(u'{{[Nn](r|umérotation)\|([^}]*)\|([^}]*)\|([^}]*)}}', text)
    if match:
        return True
    else:
        match = re.search(u'{{[Nn](r|umérotation)\|([^}]*)\|([^}]*)}}', text)
        if match:
            return True
    return False

def do_diff(ocr_text, text, opt):
    if opt.ignore_punct:
        p = re.compile(ur'[\W]+', re.U)
    else:
        p = re.compile(ur' +', re.U)

    ocr_text = p.split(ocr_text)
    text = p.split(text)

    ocr_text = [x for x in ocr_text if x]
    text = [x for x in text if x]

    diff = run_diff(ocr_text, text)

    diff = re.sub(u'^--- /[^\n]+/[^\n]+\n', '', diff)
    diff = re.sub(u'^\+\+\+ /[^\n]+/[^\n]+\n', '', diff)

    diff = re.split(u'(?ms)@@.*?@@\n', diff)
    diff = [x for x in diff if x]

    return diff

def filter_diff(diff, opt):
    result = []
    for d in diff:
        if check_diff(d, opt):
            result.append(d)

    return result

def do_transform(text, ocr_text, opt):
    text = common_transform(text)
    text = transform_text(text, opt)
    ocr_text = common_transform(ocr_text)
    ocr_text = transform_ocr_text(ocr_text, opt)
    return text, ocr_text

def verify_match(page_name, ocr_text, text, opt):
    has_nr = has_nr_template(text)

    if opt.do_transform:
        text, ocr_text = do_transform(text, ocr_text, opt)

    diff = do_diff(ocr_text, text, opt)
    if opt.ignore_nr or not has_nr:
        ocr_text = ocr_text.split(u'\n')
        ocr_text = u'\n'.join(ocr_text[1:])
        diff2 = do_diff(ocr_text, text, opt)
        if len(diff2) < len(diff):
            #print >> sys.stderr, page_name.encode('utf-8'), "removing first line"
            diff = diff2

    diff = filter_diff(diff, opt)

    result = u''
    if len(diff):
            result += u'* [[' + page_name + u']]\n'
    for d in diff:
        d = d.split(u'\n')
        moins = u' '.join([x[1:] for x in d if len(x) > 1 and x[0] in u'-'])
        plus = u' '.join([x[1:] for x in d if len(x) > 1 and x[0] in u'+'])
        if len(moins) + len(plus):
            result += u'<pre>'
            if len(moins):
                result += u'-' + moins + u'\n'
            if len(plus):
                result += u'+' + plus + u'\n'
            result += u'</pre>\n'

    return result

def read_djvu(book_name, datas, opt):
    import align
    # FIXME: avoid to reload the cache each time
    cache = lifo_cache.LifoCache('verify_match_text_layer')
    data = align.get_djvu(cache, opt.site, book_name, True)
    for pos, text in enumerate(data):
        text = re.sub(u'(?ms)<noinclude>(.*?)</noinclude>', u'', text)
        datas.setdefault(pos + 1, [])
        datas[pos + 1].append(text)

def main(book_name, opt):
    link = pywikibot.Link(book_name, opt.site)
    book_name = link.title.replace(u' ', u'_')

    # FIXME: it's not really clever to reopen the cache for each run.
    # FIXME: we must store in the cache the sha1 of the djvu and compare
    # it to the one stored in the djvu cache to invalidate this one
    # on djvu change.
    cache = lifo_cache.LifoCache('verify_match_diff')
    cached_diff = cache.get(book_name + '.dat')
    if not cached_diff:
        cached_diff = {}

    pages = load_pages(book_name, opt, cached_diff)

    datas = {}
    rev_ids = {}
    for it in pages:
        rev_ids[it[1]] = it[2]
        datas[it[1]] = [ it[0] ]

    read_djvu(book_name, datas, opt)

    keys = datas.keys()
    keys.sort()

    title = book_name.replace(u'_', u' ')
    index_ns_name = index_prefixes['wikisource'][opt.lang]
    page_ns_name = page_prefixes['wikisource'][opt.lang]
    result = u'[[' + index_ns_name + ':' + title + u']]\n\n'
    for key in keys:
        # This check is needed if some pages or all pages doesn't contain a
        # text layer, rather to flood with a huge diff we generate nothing.
        if len(datas[key]) == 2:
            page_name = page_ns_name + u':' + title + u'/' + unicode(key)
            if datas[key][0] != None:
                temp = verify_match(page_name, datas[key][1], datas[key][0], opt)
            else:
                temp = cached_diff[key][1]

            cached_diff[key] = (rev_ids[key], temp)
            if len(temp) + len(result) > 1000 * 1000:
                result = u"\n\n'''Diff trop volumineux, résultat tronqué'''\n\n" + result
                break
            result += temp

    if opt.save:
        page = pywikibot.Page(opt.site, link.canonical_title() + u'/Diff')
        page = page.toggleTalkPage()
        page.put(result, comment = u'Mise à jour')
    else:
        print result.encode('utf-8')

    cache.set(book_name + '.dat', cached_diff)

def default_options():
    class Options:
        pass

    options = Options()
    options.lang = u'fr'
    options.site = pywikibot.getSite(code = options.lang, fam = 'wikisource')
    # By default this script write on a wiki page.
    options.save = True
    # FIXME: If you change these options, you must stop the server, delete
    # the cache 'extract_text_layer_diff' and restart the server. TODO
    # save this option to the cache and detect any change.
    options.ignore_nr = False
    options.upper_case = False
    options.do_transform = True
    options.ignore_punct = False

    return options

if __name__ == "__main__":

    options = default_options()
    options.save = False

    for arg in sys.argv[1:]:
        if arg == '-ignore_nr':
            options.ignore_nr = True
        elif arg == '-help':
            print sys.argv[0], "-ignore_nr"
            sys.exit(1)
        else:
            gen = [ { u'title' : unicode(arg, 'utf-8') } ]

    try:
        for p in gen:
            print >> sys.stderr, p[u'title'].encode('utf-8')
            if p[u'title'].endswith(u'.pdf'):
                continue
            main(p[u'title'], options)
    finally:
        pywikibot.stopme()
