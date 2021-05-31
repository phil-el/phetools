# GPL V2, author phe

import sys
import os

sys.path.append(os.path.expanduser('~/wikisource'))
from ws_namespaces import page as page_prefixes, index as index_prefixes

import re
import tempfile
import os
from common import ws_utils
from common import utils
import pywikibot
from pywikibot import pagegenerators as pagegen


def is_imported_page(text):
    if re.search(r'{{[iI]wpage[ ]*\|[^}]+}}', text):
        return True
    return False


def load_pages(book_name, opt, cache):
    # It's more efficient to do two pass, in the first we don't preload
    # contents but only check if the cache is ok.
    remaining_pages = []
    pages = []
    page_ns_name = page_prefixes['wikisource'][opt.lang]
    page_name = page_ns_name + ':' + book_name + '/'
    gen = pagegen.PrefixingPageGenerator(page_name, site=opt.site)
    for p in gen:
        page_nr = int(re.match(r'.*/(\d+)$', p.title()).group(1))
        if not cache.has_key(page_nr) or cache[page_nr][0] != p.latestRevision():
            remaining_pages.append(p)
        else:
            pages.append((None, page_nr, p.latestRevision()))

    # and in the second pass we preload contents for cache miss,
    # imported pages are never cached, but that's not a no big deal
    for p in pagegen.PreloadingGenerator(remaining_pages):
        text = p.get()
        if not is_imported_page(text):
            page_nr = int(re.match(r'.*/(\d+)$', p.title()).group(1))
            pages.append((text, page_nr, p.latestRevision()))

    return pages


# FIXME: share
def strip_link(matchobj):
    link = matchobj.group(1)
    # break image with legend, it doesn't look like sensible to use this
    # in a section title
    if link.startswith('Image:') or link.startswith('image:'):
        return ''
    link = link.split('|')
    link = link[-1]
    return link


def remove_template_pass(text):
    text = re.sub('{{[Ee]r}}', 'er', text)
    text = re.sub('{{[Mm]me}}', 'Mme', text)
    text = re.sub('{{[Mm]r}}', 'Mr', text)
    text = re.sub('{{[Mm]lle}}', 'Mlle', text)
    text = re.sub('{{[Mm]lles}}', 'Mlles', text)
    text = re.sub('{{[Mm]mes}}', 'Mmes', text)
    text = re.sub('{{[Mm]gr}}', 'Mgr', text)
    text = re.sub('{{[Mm]e}}', 'Me', text)
    text = re.sub('{{[Mm]ME}}', 'MME', text)
    text = re.sub('{{[Dd]r}}', 'Dr', text)
    text = re.sub(r'{{…\|[^}]*}}', '', text)
    text = re.sub('{{[fF]ormatnum:([^{}]*?)}}', r'\1', text)
    text = re.sub(r'{{[tT]iret\|([^{}]*?)\|[^{}]*?}}', r'\1-', text)
    text = re.sub('{{[sS]éparateur}}', '', text)
    text = re.sub(r'{{[sS]éparateur de points(\|[^{}]*)?}}', '', text)
    text = re.sub(r'{{[sS]p\|([^{}|]*)}}', r'\1', text)
    text = re.sub(r'{{[sS]\|([^{}|]*)}}', r'\1e siècle', text)
    text = re.sub(r'{{[sS]\|([^{}|]*)\|e}}', r'\1e siècle', text)
    text = re.sub(r'{{[sS]\|([^{}|]*)\|er}}', r'\1er siècle', text)
    text = re.sub(r'{{[sS]\|([^{}|]*)\|([^{}|]*)\|s}}', r'\1\2 siècles', text)
    text = re.sub(r'{{[sS]\|([^{}|]*)\|([^{}|]*)\|-}}', r'\1\2', text)
    text = re.sub(r'{{[sS]p\|[^{}]*\|([^{}]*)}}', r'\1', text)
    text = re.sub(r'{{[aA]ngle\|([^{}]*)\|([^{}]*)\|([^{}]*)\|([^{}]*)}}', r'\1 \2 \3 \4', text)
    text = re.sub(r'{{[aA]ngle\|([^{}]*)\|([^{}]*)\|([^{}]*)}}', r'\1 \2 \3', text)
    text = re.sub(r'{{[aA]ngle\|([^{}]*)\|([^{}]*)}}', r'\1 \2 ', text)
    text = re.sub(r'{{[Ii]nitiale\|([^{}|]*(\|[^{}]*)*)}}', r'\1', text)
    text = re.sub('{{=}}', '', text)
    text = re.sub(r'{{[sS]éparateur\|[^{}]*}}', '', text)
    text = re.sub(r'{{[aA]\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[aA]linéa\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[fF]AD\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[fF]lotteADroite\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[aA]linéa\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[dD]\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[dD]roite\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[gG]\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[gG]auche\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[tT]iret2\|[^{}]*?\|([^{}]*?)}}', r'\1', text)
    text = re.sub(r'{{[Ll]ang\|[^{}]*?\|([^{}]*?)}}', r'\1', text)
    text = re.sub(r'{{[tT]aille\|([^{}]*?)\|[^{}]*?}}', r'\1', text)
    text = re.sub(r'{{[tT]\|([^{}]*?)\|[^{}]*?}}', r'\1', text)
    text = re.sub(r'{{[Cc]orr\|([^{}]*?)\|[^{}]*?}}', r'\1', text)
    text = re.sub(r'{{[eE]\|([^{}]*?)}}', r'\1', text)
    text = re.sub('{{[eE]}}', 'e', text)
    text = re.sub(r'{{[Cc]itation\|([^{}]*?)}}', r'\1', text)
    text = re.sub(r'{{[Cc]aché\|[^{}]*?}}', '', text)
    text = re.sub(r'(?ms){{([Cc]|[Cc]entré)\|([^{}]*?)(\|[^{}]*)*}}', r'\2', text)
    text = re.sub(r'{{[PpSs]c\|([^{}]*?)}}', r'\1', text)
    text = re.sub(r'{{[tT][234]\|([^{}|]*?)(\|(fs|sp|lh|align)[ ]*=[ ]*[^}]*)*}}', r'\1', text)
    text = re.sub(r'{{[tT][234]\|([^{}]*?)\|([^{}]*?)(\|(fs|sp|lh|align)[ ]*=[ ]*[^}]*)*}}', r'\2 \1', text)
    text = re.sub(r'{{[tT][234]\|([^{}|]*?)}}', r'\1', text)
    text = re.sub(r'{{[tT][234]\|([^{}]*?)\|([^{}]*?)}}', r'\2 \1', text)
    text = re.sub(r'{{[tT][1234]mp\|([^{}|]*?)}}', r'\1', text)
    text = re.sub(r'{{[lL]ettrine\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[Rr]efa\|([^{}|]*)\|([^{}]*)}}', r'\2', text)
    text = re.sub(r'{{[Rr]efa\|([^{}|]*)}}', r'\1', text)
    text = re.sub(r'{{[Rr]efl\|([^{}]*)\|num=([^{}]*)}}', r'\2', text)
    text = re.sub(r'{{[Rr]efl\|([^{}|]*)\|nosup}}', r'\1', text)
    text = re.sub(r'{{[Rr]efl\|([^{}|]*)}}', r'\1', text)
    text = re.sub(r'{{[Pp]li\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{-[-]+(\|[^{}]*)*}}', '', text)
    text = re.sub(r'{{[Bb]rn\|[^{}]*}}', '', text)
    text = re.sub(r'{{[Pp]ersonnage\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[Pp]ersonnageD\|([^{}|]*)\|[^|{}]*\|([^|{}]*)(\|[^{}]*)*}}', r'\1 \2', text)
    text = re.sub(r'{{[Dd]idascalie\|([^{}|]*)(\|[^{}]*)*}}', r'\1', text)
    text = re.sub(r'{{[Aa]stérisme(\|[^{}]*)*}}', '', text)
    text = re.sub(r'{{[Aa]stérisque(\|[^{}]*)*}}', '', text)
    text = re.sub(r'{{[Pp]etitTitre\|([^{}|]*)}}', r'\1', text)
    text = re.sub(r'{{[Pp]etitTitre2\|([^{}|]*)}}', r'\1', text)
    text = re.sub(r'(?ms){{[Éé]pigraphe\|([^{}|]*)}}', r'\1', text)
    text = re.sub(r'(?ms){{[Éé]pigraphe\|([^{}]*?)\|([^{}]*?)}}', r'\1 \2', text)
    text = re.sub(r'{{—[ ]*\|([^{}]*)}}', '', text)
    text = re.sub(r'{{\.\.\.\|([^{}]*)}}', '', text)

    return text


def remove_template(text):
    old_text = None
    while old_text != text:
        old_text = text
        text = remove_template_pass(text)
    return text


def remove_ocr_template_pass(text):
    text = re.sub(r'{{[Ss]c\|([^{}]*?)}}', r'\1', text)
    return text


def remove_ocr_template(text):
    old_text = None
    while old_text != text:
        old_text = text
        text = remove_ocr_template_pass(text)
    return text


def remove_tag_pass(text):
    text = re.sub('(?msi)<div[^>]*?>(.*?)</div>', r'\1', text)
    text = re.sub('(?msi)<sup[^>]*?>(.*?)</sup>', r'\1', text)
    text = re.sub('(?msi)<includeonly[^>]*?>(.*?)</includeonly>', '', text)
    text = re.sub('(?msi)<span[^>]*?>(.*?)</span>', r'\1', text)
    text = re.sub('(?msi)<big[^>]*?>(.*?)</big>', r'\1', text)
    text = re.sub('(?msi)<small[^>]*?>(.*?)</small>', r'\1', text)
    text = re.sub('(?msi)<i[^>]*?>(.*?)</i>', r'\1', text)
    text = re.sub('(?msi)<center[^>]*?>(.*?)</center>', r'\1', text)
    text = re.sub('(?msi)<poem[^>]*?>(.*?)</poem>', r'\1', text)
    return text


def remove_tag(text):
    old_text = None
    while old_text != text:
        old_text = text
        text = remove_tag_pass(text)
    return text


def explode_template_params(text):
    result = {}
    for it in re.finditer(r'([\w]+)[ ]*=[ ]*([^|}]*)', text):
        result[it.group(1)] = it.group(2)
    return result


def handle_table(text):
    tables = []
    for it in re.finditer(r'(?ms){{[tT]able[ ]*\|[^}]*?}}', text):
        tables.append((it.start(0), it.end(0)))
    tables.sort(reverse=True)
    for t in tables:
        result = explode_template_params(text[t[0]:t[1]])
        new_text = ''
        if result.has_key('section'):
            new_text += result['section'] + ' '
        if result.has_key('titre'):
            new_text += result['titre'] + ' '
        if result.has_key('page'):
            new_text += result['page'] + ' '
        text = text[0:t[0]] + ' ' + new_text + text[t[1]:]
    # if len(tables):
    #    print(text)
    return text


def common_transform(text):
    text = text.replace('…', '...')
    text = re.sub("'''([^']*)'''", r'\1', text)
    text = re.sub("''([^']*)''", r'\1', text)
    text = text.replace("'", "’")
    text = text.replace('ſ', 's')
    return text


def transform_text(text, opt):
    header, text, footer = ws_utils.split_page_text(text)
    text = re.sub('(?msi)<noinclude[^>]*?>(.*?)</noinclude>', r'\1', text)
    text = re.sub('\n[:]+', '\n', text)

    text = remove_tag(text)
    text = re.sub("'''([^']*)'''", r'\1', text)
    text = re.sub("''([^']*)''", r'\1', text)
    text = re.sub('(?msi)<section[^>]*?/>', '', text)
    text = re.sub('(?msi)<br[^>]*?>', ' ', text)
    text = re.sub('(?msi)<nowiki[^>]*?>', '', text)
    text = re.sub('(?msi)</nowiki[^>]*?>', '', text)
    text = remove_template(text)
    text = re.sub(r'\[\[([^\]]*?)\]\]', strip_link, text)
    text = text.replace('__NOTOC__', '')
    text = re.sub('style="[^"]*"', '', text)
    text = re.sub("style='[^']*'", '', text)
    text = re.sub('cellpadding="[0-9]+"', '', text)
    text = re.sub("cellpadding='[0-9]+'", '', text)
    text = re.sub("cellpadding=[0-9]+", '', text)
    text = re.sub('cellspacing="[0-9]+"', '', text)
    text = re.sub("cellspacing='[0-9]+'", '', text)
    text = re.sub("cellspacing=[0-9]+", '', text)
    text = re.sub('rowspan="[0-9]+"', '', text)
    text = re.sub("rowspan='[0-9]+'", '', text)
    text = re.sub("rowspan=[0-9]+", '', text)
    text = re.sub('colspan="[0-9]+"', '', text)
    text = re.sub("colspan='[0-9]+'", '', text)
    text = re.sub("colspan=[0-9]+", '', text)
    text = re.sub('border="[0-9]+"', '', text)
    text = re.sub("border='[0-9]+'", '', text)
    text = re.sub("border=[0-9]+", '', text)
    text = re.sub('align="(left|right|center|justify)"', '', text)
    text = re.sub("align='(left|right|center|justify)'", '', text)
    text = re.sub("align=(left|right|center|justify)", '', text)
    text = re.sub('valign="(top|middle|bottom)"', '', text)
    text = re.sub("valign='(top|middle|bottom)'", '', text)
    text = re.sub("valign=(top|middle|bottom)", '', text)
    text = re.sub('width="[0-9]+(em|px|%)"', '', text)
    text = re.sub("width='[0-9]+(em|px|%)'", '', text)
    text = re.sub("width=[0-9]+(em|px|%)", '', text)

    text = re.sub('__+', '', text)
    text = text.replace('&nbsp;', ' ')

    # FIXME: numérotation is center|left|right
    match = re.search(r'{{[Nn](r|umérotation)\|([^|}]*)\|([^|}]*)\|([^|}]*)}}', header)
    if match:
        text = match.group(2) + ' ' + match.group(3) + ' ' + match.group(4) + '\n' + text
    else:
        match = re.search(r'{{[Nn](r|umérotation)\|([^|}]*)\|([^|}]*)}}', header)
        if match:
            text = match.group(2) + ' ' + match.group(3) + '\n' + text

    # move downward all ref. First ref follow to ensure the right order
    refs = []
    for it in re.finditer('(?msi)<ref follow=[^>]*>(.*?)</ref>', text):
        refs.append(it.group(1))
    for it in re.finditer('(?msi)<ref( name=[^>]*)*>(.*?)</ref>', text):
        refs.append(it.group(2))
    text = re.sub('(?msi)<ref( name=[^>]*)*>.*?</ref>', '', text)
    for ref in refs:
        text += '\n' + ref

    text = re.sub('(?msi)<ref follow=[^>]*>.*?</ref>', '', text)

    text = handle_table(text)

    if opt.upper_case:
        text = text.upper()
    return text


def transform_ocr_text(ocr_text, opt):
    ocr_text = re.sub('\n«[ ]*', '\n', ocr_text)
    ocr_text = re.sub('-[ ]*\n', '', ocr_text)
    ocr_text = remove_ocr_template(ocr_text)
    ocr_text = ocr_text.replace('\\037', '')
    ocr_text = ocr_text.replace('\\035', '')
    ocr_text = ocr_text.replace('\\013', '')
    if opt.upper_case:
        ocr_text = ocr_text.upper()
    return ocr_text


def run_diff(ocr_text, text, opt):
    ocr_text = "\n".join(ocr_text) + "\n"
    temp1 = tempfile.NamedTemporaryFile(suffix='.txt')
    utils.write_file(temp1.name, ocr_text)
    text = "\n".join(text) + "\n"
    temp2 = tempfile.NamedTemporaryFile(suffix='.txt')
    utils.write_file(temp2.name, text)
    cmdline = "diff -U %d " % opt.diff_context + temp1.name + " " + temp2.name
    fd = os.popen(cmdline)
    diff = ''
    for t in fd.readlines():
        diff += t
    fd.close()

    return diff


def white_list(left, right):
    lst = {
        'CLANS': 'DANS',
        'CELTE': 'CETTE',
        "CLOUTE": "DOUTE",
        "INONDE": "MONDE",
        "CLOUTAIS": "DOUTAIS",
        "GRECLINS": "GREDINS",
        "GRECLIN": "GREDIN",
        "CLOUTER": "DOUTER",
        "CLOUTÂT": "DOUTÂT",
        "CLIGNE": "DIGNE",
        "US": "ILS",
        "CLAMES": "DAMES",
        "CLAME": "DAME",
        "TON": "L’ON",
        "JUE": "QUE",
        "CJUE": "QUE",
        "FDLES": "FILLES",
        "FDLE": "FILLE",
        "H": "À",
        "A": "À",
        "I": "",
        "TÉtat": "L’ÉTAT",
    }

    if left in lst and right == lst[left]:
        return True
    return False


def transform_ocr_diff(diff):
    diff = diff.replace('OEUVRÉ', 'ŒUVRÉ')
    diff = diff.replace('COETERA', 'CÆTERA')
    diff = diff.replace('VOEUX', 'VŒUX')
    diff = diff.replace('MOEURS', 'MŒURS')
    diff = diff.replace('SOEUR', 'SŒUR')
    diff = diff.replace('CHOEUR', 'CHŒUR')
    diff = diff.replace('NOEUD', 'NŒUD')
    diff = diff.replace('VOEUX', 'VŒUX')
    diff = diff.replace('COEUR', 'CŒUR')
    diff = diff.replace('OEUVRE', 'ŒUVRE')
    diff = diff.replace('GOETHE', 'GŒTHE')
    diff = diff.replace('HAENDEL', 'HÆNDEL')
    diff = diff.replace('OEIL', 'ŒIL')
    diff = diff.replace('OEUF', 'ŒUF')
    diff = diff.replace('A', 'À')

    return diff


def check_diff(text, opt):
    text = text.split('\n')
    left = ''.join([x[1:] for x in text if len(x) > 1 and x[0] == '-'])
    right = ''.join([x[1:] for x in text if len(x) > 1 and x[0] == '+'])
    # if (re.search(u'DE', right) and re.search(u'À', left)) or (re.search(u'DE', left) and re.search(u'À', right)):
    #    print(right)
    #    print(left)
    if len(left) <= 3 and len(right) <= 3:
        if re.search('[0-9]', left) or re.search('[0-9]', right):
            return False
    if white_list(left.upper(), right.upper()):
        return False
    # print(left)
    # print(right)
    return True


def has_nr_template(text):
    match = re.search(r'{{[Nn](r|umérotation)\|([^|}]*)\|([^|}]*)\|([^|}]*)}}', text)
    if match:
        return True
    else:
        match = re.search(r'{{[Nn](r|umérotation)\|([^|}]*)\|([^|}]*)}}', text)
        if match:
            return True
    return False


def do_diff(ocr_text, text, opt):
    if opt.ignore_punct:
        p = re.compile(r'[\W]+', re.U)
    else:
        p = re.compile(r'[ \r\n]+', re.U)

    ocr_text = p.split(ocr_text)
    text = p.split(text)

    ocr_text = [x for x in ocr_text if x]
    text = [x for x in text if x]

    diff = run_diff(ocr_text, text, opt)

    diff = re.sub(r'^--- /[^\n]+/[^\n]+\n', '', diff)
    diff = re.sub(r'^\+\+\+ /[^\n]+/[^\n]+\n', '', diff)

    diff = re.split('(?ms)@@.*?@@\n', diff)
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
    if False and not has_nr:
        ocr_text = ocr_text.split('\n')
        ocr_text = '\n'.join(ocr_text[1:])
        diff2 = do_diff(ocr_text, text, opt)
        if len(diff2) < len(diff):
            diff = diff2
    elif False:
        ocr_text = ocr_text.split('\n')
        ocr_text = '\n'.join(ocr_text[1:])
        text = text.split('\n')
        text = '\n'.join(text[1:])
        diff2 = do_diff(ocr_text, text, opt)
        if len(diff2) < len(diff):
            diff = diff2

    diff = filter_diff(diff, opt)

    result = ''
    if len(diff):
        result += '* [[' + page_name + ']]\n'
    for d in diff:
        d = d.split('\n')
        moins = ' '.join([x[1:] for x in d if len(x) > 1 and x[0] in ' -'])
        plus = ' '.join([x[1:] for x in d if len(x) > 1 and x[0] in ' +'])
        if len(moins) + len(plus):
            result += '<pre>'
            if len(moins):
                result += '-' + moins + '\n'
            if len(plus):
                result += '+' + plus + '\n'
            result += '</pre>\n'

    return result


def read_djvu(book_name, cached_text, datas, opt):
    from match_and_split import align
    data = align.get_djvu(cached_text, opt.site, book_name, True)
    for pos, text in enumerate(data):
        text = re.sub('(?ms)<noinclude>(.*?)</noinclude>', '', text)
        datas.setdefault(pos + 1, [])
        datas[pos + 1].append(text)


def main(book_name, cached_diff_cache, cached_text_cache, opt):
    link = pywikibot.Link(book_name, opt.site)
    book_name = link.title.replace(' ', '_')

    # FIXME: we must store in the cache the sha1 of the djvu and compare
    # it to the one stored in the djvu cache to invalidate this one
    # on djvu change.
    cached_diff = cached_diff_cache.get(book_name + '.dat')
    if not cached_diff:
        cached_diff = {}

    pages = load_pages(book_name, opt, cached_diff)

    datas = {}
    rev_ids = {}
    for it in pages:
        rev_ids[it[1]] = it[2]
        datas[it[1]] = [it[0]]

    read_djvu(book_name, cached_text_cache, datas, opt)

    keys = datas.keys()
    keys.sort()

    title = book_name.replace('_', ' ')
    index_ns_name = index_prefixes['wikisource'][opt.lang]
    page_ns_name = page_prefixes['wikisource'][opt.lang]
    result = '[[' + index_ns_name + ':' + title + ']]\n\n'
    for key in keys:
        # This check is needed if some pages or all pages doesn't contain a
        # text layer, rather to flood with a huge diff we generate nothing.
        if len(datas[key]) == 2:
            page_name = page_ns_name + ':' + title + '/' + unicode(key)
            if datas[key][0] != None:
                temp = verify_match(page_name, datas[key][1], datas[key][0], opt)
            else:
                temp = cached_diff[key][1]

            cached_diff[key] = (rev_ids[key], temp)
            if len(temp) + len(result) > 1000 * 1000:
                result = "\n\n'''Diff trop volumineux, résultat tronqué'''\n\n" + result
                break
            result += temp

    if opt.save:
        page = pywikibot.Page(opt.site, link.canonical_title() + '/Diff')
        page = page.toggleTalkPage()
        page.put(result, comment='Mise à jour')
    else:
        print(result)

    cached_diff_cache.set(book_name + '.dat', cached_diff)


def default_options():
    class Options:
        pass

    options = Options()
    options.lang = 'fr'
    options.site = pywikibot.Site(code=options.lang, fam='wikisource')
    # By default this script write on a wiki page.
    options.save = True
    # FIXME: If you change these options, you must stop the server, delete
    # the cache 'extract_text_layer_diff' and restart the server. TODO
    # save this option to the cache and detect any change.
    options.upper_case = False
    options.do_transform = True
    options.ignore_punct = False
    options.diff_context = 1

    return options


if __name__ == "__main__":

    options = default_options()
    options.save = False

    for arg in sys.argv[1:]:
        if arg == '-help':
            print(sys.argv[0], "")
            sys.exit(1)
        elif arg.startswith('-diff_context'):
            options.diff_context = int(arg[len('-diff_context:'):])
        else:
            gen = [{'title': arg}]

    try:
        for p in gen:
            print(p['title'], file=sys.stderr)
            if p['title'].endswith('.pdf'):
                continue
            main(p['title'], options)
    finally:
        pywikibot.stopme()
