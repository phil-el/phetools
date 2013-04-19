# -*- coding: utf-8 -*-

import sys
sys.path.append("/home/phe/pywikipedia")
import wikipedia
import query_ext
import lev_dist
import re
import tempfile
import os
import ws_utils
import utils

def is_imported_page(text):
    if re.search(u'{{[iI]wpage[ ]*\|[^}]+}}', text):
        return True
    return False

def load_pages(book_name, opt):
    gen = query_ext.PreloadingPagesStartswith(u'Page:' + book_name + u'/',
                                              site = opt.site)
    pages = []
    for p in query_ext.PreloadingContents(gen, site = opt.site):
        #print >> sys.stderr, p[u'title'].encode('utf-8')
        text = p[u'revisions'][0]['*']
        if not is_imported_page(text):
            page_nr = int(re.match(u'.*/(\d+)$', p[u'title']).group(1))
            pages.append( ( text, page_nr ) )
    return pages

# return the djvu filename
def get_djvu_name(book_name):
    djvu_name = 'DJVU/' + book_name.encode('utf-8')
    djvu_name = djvu_name.replace(' ', '_')
    return djvu_name

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
    text = re.sub(u'{{[fF]ormatnum:([^{}]*?)}}', u'\\1', text)
    text = re.sub(u'{{[tT]iret\|([^{}]*?)\|[^{}]*?}}', u'\\1', text)
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
    text = re.sub(u'{{[Aa]stérisme(\|[^{}]*)*}}', u'', text)
    text = re.sub(u'{{[Aa]stérisque(\|[^{}]*)*}}', u'', text)
    text = re.sub(u'{{[Pp]etitTitre\|([^{}|]*)}}', u'\\1', text)
    text = re.sub(u'{{[Pp]etitTitre2|([^{}|]*)}}', u'\\1', text)

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
    text = re.sub(u'(?msi)<br[^>]*?>', u'', text)
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

    text = text.upper()
    return text

def transform_ocr_text(ocr_text, opt):
    ocr_text = remove_ocr_template(ocr_text)
    ocr_text = ocr_text.replace(u'\\037', u'')
    ocr_text = ocr_text.replace(u'\\035', u'')
    ocr_text = ocr_text.replace(u'\\013', u'')
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
    return diff

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
        }

    if left in lst and right == lst[left]:
        return True
    return False

def check_distance(left, right):
    dist = lev_dist.distance(left, right)
    if dist > 1:
        if dist <= 4 and ((len(left) + len(right)) / dist) >= 10:
            return False
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

def check_diff(text):
    text = text.split(u'\n')
    left = u''.join([ x[1:] for x in text if len(x) > 1 and x[0] == '-' ])
    right= u''.join([ x[1:] for x in text if len(x) > 1 and x[0] == '+' ])
    #if (re.search(u'DE', right) and re.search(u'À', left)) or (re.search(u'DE', left) and re.search(u'À', right)):
    #    print right
    #    print left
    if len(left) <= 3 and len(right) <= 3:
        if re.search(u'[0-9]', left) or re.search(u'[0-9]', right):
            return False
    if white_list(left, right):
        return False
    #print left.encode('utf-8')
    #print right.encode('utf-8')
    if check_distance(left, right):
        left = transform_ocr_diff(left)
        return check_distance(left, right)
    return False

def has_nr_template(text):
    match = re.search(u'{{[Nn](r|umérotation)\|([^}]*)\|([^}]*)\|([^}]*)}}', text)
    if match:
        return True
    else:
        match = re.search(u'{{[Nn](r|umérotation)\|([^}]*)\|([^}]*)}}', text)
        if match:
            return True
    return False

def do_diff(ocr_text, text):
    p = re.compile(ur'[\W]+', re.U)

    ocr_text = p.split(ocr_text)
    text = p.split(text)

    ocr_text = [x for x in ocr_text if x]
    text = [x for x in text if x]

    diff = run_diff(ocr_text, text)

    diff = re.sub('^--- /[^\n]+/[^\n]+\n', '', diff)
    diff = re.sub('^\+\+\+ /[^\n]+/[^\n]+\n', '', diff)

    diff = re.split(u'(?ms)@@.*?@@\n', diff)
    diff = [x for x in diff if x]

    return diff

def filter_diff(diff):
    result = []
    for d in diff:
        d = unicode(d, 'utf-8')
        if check_diff(d):
            result.append(d)

    return result

def verify_match(page_name, ocr_text, text, opt):
    has_nr = has_nr_template(text)

    text = common_transform(text)
    text = transform_text(text, opt)
    ocr_text = common_transform(ocr_text)
    ocr_text = transform_ocr_text(ocr_text, opt)

    diff = do_diff(ocr_text, text)
    if opt.ignore_nr or not has_nr:
        ocr_text = ocr_text.split(u'\n')
        ocr_text = u'\n'.join(ocr_text[1:])
        diff2 = do_diff(ocr_text, text)
        if len(diff2) < len(diff):
            #print >> sys.stderr, page_name.encode('utf-8'), "removing first line"
            diff = diff2

    diff = filter_diff(diff)

    result = u''
    if len(diff):
            result += u'* [[' + page_name + u']]\n'
    for d in diff:
        d = d.split(u'\n')
        d = u'\n'.join([x for x in d if len(x) > 1 and x[0] in u'-+'])
        result += u'<pre>' + d + u'\n</pre>' + u'\n'

    return result

def read_djvu(book_name, datas, opt):
    try:
        import ocr_rate
        filename = get_djvu_name(book_name)
        for it in ocr_rate.read_objects(filename):
            datas.setdefault(it[0], [])
            datas[it[0]].append(it[1])
    except:
        import align
        filename = align.get_djvu(opt.site, book_name, True)
        if not filename:
            return False
        for i in range(1, align.get_nr_djvu_pages(filename) + 1):
            text = align.read_djvu_page(filename, i)
            text = re.sub(u'(?ms)<noinclude>(.*?)</noinclude>', u'', text)
            datas.setdefault(i, [])
            datas[i].append(text)
    return True

def main(book_name, opt):
    book_name = book_name[len(u'Livre:'):]

    pages = load_pages(book_name, opt)

    datas = {}
    for it in pages:
        datas[it[1]] = [ it[0] ]

    if not read_djvu(book_name, datas, opt):
        return False

    keys = datas.keys()
    keys.sort()

    result = u'[[Livre:' + book_name + u']]\n\n'
    for key in keys:
        if len(datas[key]) == 2:
            page_name = u'Page:' + book_name + u'/' + unicode(key)
            temp = verify_match(page_name, datas[key][1], datas[key][0], opt)
            if len(temp) + len(result) > 384 * 1024:
                result = u"\n\n'''Diff trop volumineux, résultat tronqué'''\n\n" + result
                break
            result += temp

    #print result.encode('utf-8')
    if opt.save:
        out_page = u'Discussion Livre:' + book_name + u'/Diff'
        page = wikipedia.Page(site = opt.site, title = out_page)
        page.put(result, comment = u'Mise à jour')

    return True

def default_options():
    class Options:
        pass

    options = Options()
    options.lang = u'fr'
    options.site = wikipedia.getSite(code = options.lang, fam = 'wikisource')
    options.save = True
    options.ignore_nr = False

    return options

if __name__ == "__main__":

    options = default_options()

    for arg in sys.argv[1:]:
        if arg.startswith('-links:'):
            name = arg[len('-links:'):]
            name = unicode(name, 'utf-8')
            extraParms = { u'gplnamespace' : 112 }
            gen = query_ext.PreloadingLinkedPage([name], site = options.site, extraParams = extraParms)
        elif arg == '-ignore_nr':
            options.ignore_nr = True
        elif arg == '-help':
            print sys.argv[0], "-links -ignore_nr"
            sys.exit(1)
        else:
            gen = [ { u'title' : unicode(arg, 'utf-8') } ]

    try:
        found = False
        for p in gen:
            print >> sys.stderr, p[u'title'].encode('utf-8')
            #if p[u'title'] == u'Livre:Régnier Double maîtresse 1900.djvu':
            found = True
            if p[u'title'].endswith(u'.pdf'):
                continue
            if not found:
                continue
            main(p[u'title'], options)
    finally:
        wikipedia.stopme()
