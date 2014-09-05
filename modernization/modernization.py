# -*- coding: utf-8 -*-
#
# @file modernization.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import re
import pywikibot
import pywikibot.pagegenerators as pagegen
from pywikibot.data import api
import sys
import utils
import os
import collections
import common_html
import xml.etree.ElementTree as etree
sys.path.append(os.path.expanduser('~/phe/spell'))
import spell

dict_config = {}

dict_config['pt'] = {
    'variant' : [ 'BR', 'PT' ],
    'word_chars' : u'a-zA-Z0-9áàâãçéêíñóôõúüÁÀÂÃÇÉÊÍÑÓÔÕÚ\'ºª\\-',
    'max_seq' : 3,
}

# FIXME: inneficient as we load local dict multiple time for each variant but
# it's unclear if we can assume than there is no different template for each
# variant. We could rely on caching the page list and page text to load them
# only once (but it'll require two parsing anyway ?)

dict_config['pt']['BR'] = {
    'global_dict' : u'Wikisource:Modernização/Dicionário/pt-BR',
    'modernize_template' : u'Predefinição:Modernização automática',
    'modernize_div_id' : 'dic-local-BR',
    'aspell_lang' : 'pt_BR',
    'transform' : [
        # FIXME: https://pt.wikipedia.org/wiki/MediaWiki:Gadget-LanguageConverter.js
        ],
    }

dict_config['pt']['PT'] = {
    'global_dict' : u'Wikisource:Modernização/Dicionário/pt-PT',
    'modernize_template' : u'Predefinição:Modernização_automática',
    'modernize_div_id' : 'dic-local-PT',
    # need to be changed depending on aspell version. This one is ok for
    # wmflabs actually
    'aspell_lang' : 'pt',
    'transform' : [
        # FIXME:
        ],
}

dict_config['fr'] = {
    'variant' : [ 'FR' ],
    'word_chars' : u'a-zçâàäāãéèêẽëîïôöōõûùüÿœæA-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÇŒÆ&ßẞĩq̃ĨQ̃',
    'max_seq' : 3,
}

dict_config['fr']['FR'] = {
    'global_dict' : u'Wikisource:Dictionnaire',
    'modernize_template' : u'Template:Modernisation',
    'modernize_div_id' : 'modernisations',
    'aspell_lang' : 'fr',
    'transform' : [
        [ u'ſ', 's' ],
        [ u'ﬀ', 'ff' ],
        [ u'ﬂ', 'fl' ],
        [ u'ﬁ', 'fi' ],
        [ u'ﬃ', 'ffi' ],
        [ u'ﬄ', 'ffl' ],
        [ u'ﬅ', 'st' ],
        [ u'ﬆ', 'st' ],
        ],
}

def cache_filename(lang, variant):
    return os.path.expanduser('~/cache/modernization/') + lang + '_' + variant + '.dat'

def default_cache():
    return collections.OrderedDict()

def load_cache(lang, variant):
    filename = cache_filename(lang, variant)
    if not os.path.exists(filename):
        obj = default_cache()
    else:
        obj = utils.load_obj(filename)

    return obj

def save_cache(lang, variant, obj):
    filename = cache_filename(lang, variant)
    utils.save_obj(filename, obj)

def get_page(lang, title):
    site = pywikibot.Site(lang, fam = u'wikisource')
    return pywikibot.Page(site, title)

def get_local_dict_list(lang, variant):
    title = dict_config[lang][variant]['modernize_template']
    page = get_page(lang, title)
    for p in pagegen.ReferringPageGenerator(page, followRedirects=True,
                                            onlyTemplateInclusion = True):
        yield p

def get_etree_text(node, exclude):
    result = u''
    if node not in exclude:
        if node.text:
            result += node.text
        for child in node:
            result += get_etree_text(child, exclude)
        if node.tail:
            result += node.tail
    return result

def parse_global_dict(lang, variant, html):
    result = collections.OrderedDict()

    html = common_html.get_head(u'TITLE') + u"\n<body>"  + html + u'\n</body>\n</html>'
    root = etree.fromstring(html.encode('utf-8'))
    text = u''
    for it in root.findall(".//{http://www.w3.org/1999/xhtml}li"):
        text += get_etree_text(it, set())

    for line in text.split(u'\n'):
        match = re.match(u'^\s*(\S[^: ]*?)(?:\s|&#160;|&nbsp;| )*:\s*([\S].+?)\s*(?:\/\/.*?)?$', line, re.UNICODE)
        if match:
            result[match.group(1)] = match.group(2)

    return result

def parse_local_dict(lang, variant, html):
    result = collections.OrderedDict()
    html_id = dict_config[lang][variant]['modernize_div_id']

    html = common_html.get_head(u'TITLE') + u"\n<body>"  + html + u'\n</body>\n</html>'
    root = etree.fromstring(html.encode('utf-8'))
    text = u''
    for it in root.findall(".//{http://www.w3.org/1999/xhtml}div[@id='%s']" % html_id):
        text += get_etree_text(it, set())

    for line in text.split(u'\n'):
        match = re.match(u'^\s*(\S[^: ]*?)(?:\s|&#160;|&nbsp;| )*:\s*([\S].+?)\s*(?:\/\/.*?)?$', line, re.UNICODE)
        if match:
            result[match.group(1)] = match.group(2)

    return result

def get_html(page):
    req = api.Request(site=page.site, page=page.title(),
                      action='parse', prop = 'text')
    data = req.submit()
    return data['parse']['text']['*']

def get_global_dict(lang, variant):
    title = dict_config[lang][variant]['global_dict']
    return get_page(lang, title)

def update_cache_variant(lang, variant):
    old_cache = load_cache(lang, variant)
    new_cache = default_cache()
    count = 0
    for p in get_local_dict_list(lang, variant):
        if p.latestRevision() in old_cache:
            new_cache[p.latestRevision()] = old_cache[p.latestRevision()]
        else:
            count += 1
            print >> sys.stderr, count, '\r',
            html = get_html(p)
            result = parse_local_dict(lang, variant, html)
            new_cache[p.latestRevision()] = (p.title(), result)

    p = get_global_dict(lang, variant)
    if p.latestRevision() in old_cache:
        new_cache[p.latestRevision()] = old_cache[p.latestRevision()]
    else:
        count += 1
        html = get_html(p)
        result = parse_global_dict(lang, variant, html)

        new_cache[p.latestRevision()] = (p.title(), result)

    save_cache(lang, variant, new_cache)

    print '\nparsed', count

def update_cache(lang):
    for variant in dict_config[lang]['variant']:
        update_cache_variant(lang, variant)

def get_dict_redundancy(global_dict, local_dict):
    result = {}
    for key in local_dict:
        if key in global_dict and local_dict[key] == global_dict[key]:
            result[key] = local_dict[key]
    return result

def dump_redundant_words(title, redundant_words):
    if len(redundant_words):
        print title.encode('utf-8')
        for word in redundant_words:
            print '*' + word.encode('utf-8') + ':' + redundant_words[word].encode('utf-8')

def dump_non_redundant_words(title, local_dict, global_dict):
    redundant_words = get_dict_redundancy(global_dict, local_dict)
    if not len(redundant_words):
        return

    print '*[[' + title.encode('utf-8') + ']]'
    for key in local_dict:
        if not key in redundant_words:
            print '* ' + key.encode('utf-8') + ' : ' + local_dict[key].encode('utf-8')

def gen_non_redundant_words(lang, variant):
    cache = load_cache(lang, variant)
    p = get_global_dict(lang, variant)
    if p.latestRevision() in cache:
        global_dict = cache[p.latestRevision()][1]
    else:
        global_dict = collections.OrderedDict()

    for key in cache:
        if key != p.latestRevision():
            dump_non_redundant_words(cache[key][0], cache[key][1], global_dict)

def optimize_all_local_dict(lang):
    for variant in dict_config[lang]['variant']:
        gen_non_redundant_words(lang, variant)

def optimize_global_dict_variant(lang, variant):
    cache = load_cache(lang, variant)
    p = get_global_dict(lang, variant)
    if p.latestRevision() in cache:
        global_dict = cache[p.latestRevision()][1]
    else:
        global_dict = collections.OrderedDict()

    replace = {}

    for key in cache:
        if key != p.latestRevision():
            for word in cache[key][1]:
                replace.setdefault( (word, cache[key][1][word]), 0)
                replace[(word, cache[key][1][word])] += 1

    replace = [ (replace[key], key[0], key[1]) for key in replace ]

    replace.sort(reverse = True)

    for data in replace:
        if data[0] >= 5:
            print data[1].encode('utf-8'), data[2].encode('utf-8'), data[0]


def optimize_all_global_dict(lang):
    for variant in dict_config[lang]['variant']:
        optimize_global_dict_variant(lang, variant)

def check_title_variant(lang, variant, title):
    cache = load_cache(lang, variant)
    page = get_page(lang, title)

    try:
        last_rev = page.latestRevision()
    except pywikibot.exceptions.NoPage:
        print 'Page does not exist'
        return
        
    if last_rev in cache:
        print 'Found'
        local_dict = cache[last_rev][1]
        p = get_global_dict(lang, variant)
        if p.latestRevision() in cache:
            global_dict = cache[p.latestRevision()][1]
        else:
            global_dict = collection.OrderedDict()

        redundant_words = get_dict_redundancy(global_dict, local_dict)
        dump_redundant_words(title, redundant_words)

    else:
        print 'Not found'

def check_title(lang, title):
    for variant in dict_config[lang]['variant']:
        check_title_variant(lang, variant, title)

def check_cache(title, local_dict, global_dict):
    redundant_words = get_dict_redundancy(global_dict, local_dict)
    dump_redundant_words(title, redundant_words)

def check_all_title_variant(lang, variant):
    cache = load_cache(lang, variant)
    p = get_global_dict(lang, variant)
    if p.latestRevision() in cache:
        global_dict = cache[p.latestRevision()][1]
    else:
        global_dict = collections.OrderedDict()

    for key in cache:
        if key != p.latestRevision():
            check_cache(cache[key][0], cache[key][1], global_dict)

def check_all(lang):
    for variant in dict_config[lang]['variant']:
            check_all_title_variant(lang, variant)

def check_useless_char(lang, variant):
    cache = load_cache(lang, variant)
    transform = [ x[0] for x in dict_config[lang][variant]['transform'] ]
    regex = u'(' + u'|'.join(transform) + u')'
    for key in cache:
        local_dict = cache[key][1]
        for word in local_dict:
            if re.search(regex, word) or re.search(regex, local_dict[word]):
                print cache[key][0].encode('utf-8')
                print '*' + word.encode('utf-8') + ':'+ local_dict[word].encode('utf-8')

def get_useless_char(lang):
    for variant in dict_config[lang]['variant']:
        if len(dict_config[lang][variant]['transform']):
            check_useless_char(lang, variant)

def suggest_dict(lang, title):
    p = get_page(lang, title)
    html = get_html(p)

    new_html = common_html.get_head(u'TITLE') + u"\n<body>"  + html + u'\n</body>\n</html>'
    root = etree.fromstring(new_html.encode('utf-8'))

    exclude = set()

    for variant in dict_config[lang]['variant']:
        html_id = dict_config[lang][variant]['modernize_div_id']

        for it in root.findall(".//{http://www.w3.org/1999/xhtml}div[@id='%s']" % html_id):
            exclude.add(it)

    for variant in dict_config[lang]['variant']:

        word_seen = set()
        all_word = set()

        speller = spell.get_speller(dict_config[lang][variant]['aspell_lang'])
        cache = load_cache(lang, variant)
        p = get_global_dict(lang, variant)
        if p.latestRevision() in cache:
            global_dict = cache[p.latestRevision()][1]
        else:
            global_dict = []

        local_dict = parse_local_dict(lang, variant, html)

        text = get_etree_text(root, exclude)

        print text.encode('utf-8')

        for d in dict_config[lang][variant]['transform']:
            text = re.sub(d[0], d[1], text)

        # FIXME: upper/lower letter for suggest? and mimic
        # https://wikisource.org/wiki/User:Helder.wiki/Scripts/LanguageConverter.js
        regex_split = re.compile(u'([' + dict_config[lang]['word_chars'] + u']+)')
        for word in regex_split.findall(text):
            word = word.lower()
            all_word.add(word)
            if not word in word_seen and not word in local_dict and not word in global_dict and not speller.check(word.encode('utf-8')):
                word_seen.add(word)
                print '"' + word.encode('utf-8') + '"'

        for word in local_dict:
            if word in all_word:
                print '*' + word.encode('utf-8') + ' : ' + local_dict[word].encode('utf-8')

        suggest = {}
        for key in cache:
            if key != p.latestRevision():
                d = cache[key][1]
                for word in d:
                    suggest[word] = d[word]

        for word in word_seen:
            if word in suggest:
               print '*' + word.encode('utf-8') + ' : ' + suggest[word].encode('utf-8')


def test_global_dict(lang, variant):
    p = get_global_dict(lang, variant)
    html = get_html(p)
    result = parse_global_dict(lang, variant, html)
    for key in result:
        print key.encode('utf-8'), result[key].encode('utf-8')

def test_global_dict_config(lang):
    for variant in dict_config[lang]['variant']:
        test_global_dict(lang, variant)

def test_local_dict_config(lang):
    for variant in dict_config[lang]['variant']:
        for p in get_local_dict_list(lang, variant):
            print p.latestRevision()

def test_cache(lang, variant):
    obj = load_cache(lang, variant)
    save_cache(lang, variant, obj)

def test_cache_config(lang):
    for variant in dict_config[lang]['variant']:
        test_cache(lang, variant)

if __name__ == '__main__':
    lang = None
    title = None
    cmd = None
    for arg in sys.argv[1:]:
        if arg.startswith('-lang:'):
            lang = arg[len('-lang:'):]
        elif arg.startswith('-cmd:'):
            cmd = arg[len('-cmd:'):]
        elif arg.startswith('-title:'):
            title = unicode(arg[len('-title:'):], 'utf-8')
        
    if cmd == 'test':
        test_global_dict_config(lang)
        test_local_dict_config(lang)
        test_cache_config(lang)
    elif cmd == 'update':
        update_cache(lang)
    elif cmd == 'check_title':
        check_title(lang, title)
    elif cmd == 'check_all':
        check_all(lang)
    elif cmd == 'optimize_local_dict':
        optimize_all_local_dict(lang)
    elif cmd == 'optimize_global_dict':
        optimize_all_global_dict(lang)
    elif cmd == 'useless_char':
        get_useless_char(lang)
    elif cmd == 'suggest':
        suggest_dict(lang, title)
    else:
        print "unknown -cmd:", cmd
