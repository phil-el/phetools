# -*- coding: utf-8 -*-
#
# @file modernization.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import re
import sys
sys.path.append('/shared/pywikipedia/core')
sys.path.append('/shared/pywikipedia/core/externals/httplib2')
sys.path.append('/shared/pywikipedia/core/scripts')
import pywikibot
import pywikibot.pagegenerators as pagegen
from pywikibot.data import api
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
        # FIXME: https://pt.wikipedia.org/wiki/MediaWiki:Gadget-LanguageConverter.js
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

class Modernization:
    def __init__(self, lang):
        self.lang = lang
        self.variants = dict_config[lang]['variant']
        self.word_chars = dict_config[lang]['word_chars']
        self.max_seq = dict_config[lang]['max_seq']
        self.cache_dir = os.path.expanduser('~/cache/modernization/')
        self.config = {}
        for variant in self.variants:
            # FIXME: must we use a class instance per variant?
            self.config[variant] = dict_config[lang][variant]

    def cache_filename(self, variant):
        return self.cache_dir + self.lang + '_' + variant + '.dat'

    def default_cache(self):
        return collections.OrderedDict()

    def load_dicts(self, variant):
        filename = self.cache_filename(variant)
        if not os.path.exists(filename):
            cache = self.default_cache()
        else:
            cache = utils.load_obj(filename)

        return cache

    def save_dicts(self, variant, cache):
        filename = self.cache_filename(variant)
        utils.save_obj(filename, cache)

    def get_page(self, title):
        site = pywikibot.Site(self.lang, fam = u'wikisource')
        return pywikibot.Page(site, title)

    def get_local_dict_list(self, variant):
        title = self.config[variant]['modernize_template']
        page = self.get_page(title)
        for p in pagegen.ReferringPageGenerator(page, followRedirects = True,
                                                onlyTemplateInclusion = True):
            yield p

    def get_etree_text(self, node, exclude):
        result = u''
        if node not in exclude:
            if node.text:
                result += node.text
            for child in node:
                result += self.get_etree_text(child, exclude)
            if node.tail:
                result += node.tail
        return result

    def parse_global_dict(self, html):
        result = self.default_cache()

        html = common_html.get_head(u'TITLE') + u"\n<body>"  + html + u'\n</body>\n</html>'
        root = etree.fromstring(html.encode('utf-8'))
        text = u''
        for it in root.findall(".//{http://www.w3.org/1999/xhtml}li"):
            text += self.get_etree_text(it, set())

        for line in text.split(u'\n'):
            match = re.match(u'^\s*(\S[^: ]*?)(?:\s|&#160;|&nbsp;| )*:\s*([\S].+?)\s*(?:\/\/.*?)?$', line, re.UNICODE)
            if match:
                result[match.group(1)] = match.group(2)

        return result

    def parse_local_dict(self, variant, html):
        result = self.default_cache()
        html_id = self.config[variant]['modernize_div_id']

        html = common_html.get_head(u'TITLE') + u"\n<body>"  + html + u'\n</body>\n</html>'
        root = etree.fromstring(html.encode('utf-8'))
        text = u''
        for it in root.findall(".//{http://www.w3.org/1999/xhtml}div[@id='%s']" % html_id):
            text += self.get_etree_text(it, set())

        for line in text.split(u'\n'):
            match = re.match(u'^\s*(\S[^: ]*?)(?:\s|&#160;|&nbsp;| )*:\s*([\S].+?)\s*(?:\/\/.*?)?$', line, re.UNICODE)
            if match:
                result[match.group(1)] = match.group(2)

        return result

    def get_html(self, page):
        req = api.Request(site=page.site, page=page.title(),
                          action='parse', prop = 'text')
        data = req.submit()
        return data['parse']['text']['*']

    def get_global_dict(self, variant):
        title = self.config[variant]['global_dict']
        return self.get_page(title)

    def update_cache_variant(self, variant):
        old_cache = self.load_dicts(variant)
        new_cache = self.default_cache()
        count = 0
        for p in self.get_local_dict_list(variant):
            if p.latestRevision() in old_cache:
                new_cache[p.latestRevision()] = old_cache[p.latestRevision()]
            else:
                count += 1
                print >> sys.stderr, count, '\r',
                html = self.get_html(p)
                result = self.parse_local_dict(variant, html)
                new_cache[p.latestRevision()] = (p.title(), result)

        p = self.get_global_dict(variant)
        if 'global_dict' in old_cache and old_cache['global_dict'][0] == p.latestRevision():
            new_cache['global_dict'] = old_cache['global_dict']
        else:
            count += 1
            html = self.get_html(p)
            result = self.parse_global_dict(html)

            new_cache['global_dict'] = (p.latestRevision(), result)

        self.save_dicts(variant, new_cache)

        print '\nparsed', count

    def update_cache(self):
        for variant in self.variants:
            self.update_cache_variant(variant)

    def get_dict_redundancy(self, global_dict, local_dict):
        result = {}
        for key in local_dict:
            if key in global_dict and local_dict[key] == global_dict[key]:
                result[key] = local_dict[key]
        return result

    def dump_dict_entry(self, key, dictionary):
        print '*' + key.encode('utf-8') + ' : ' + dictionary[key].encode('utf-8')

    def dump_redundant_words(self, title, redundant_words):
        if len(redundant_words):
            print title.encode('utf-8')
            for word in redundant_words:
                self.dump_dict_entry(word, redundant_words)

    def dump_non_redundant_words(self, title, local_dict, global_dict):
       redundant_words = self.get_dict_redundancy(global_dict, local_dict)
       if not len(redundant_words):
           return

       print '*[[' + title.encode('utf-8') + ']]'
       for key in local_dict:
           if not key in redundant_words:
               self.dump_dict_entry(key, local_dict)

    def gen_non_redundant_words(self, variant):
        cache = self.load_dicts(variant)
        if 'global_dict' in cache:
            global_dict = cache['global_dict'][1]
        else:
            global_dict = self.default_cache()

        for key in cache:
            if key != 'global_dict':
                self.dump_non_redundant_words(cache[key][0], cache[key][1], global_dict)

    def optimize_all_local_dict(self):
        for variant in self.variants:
            self.gen_non_redundant_words(variant)

    def optimize_global_dict_variant(self, variant):
        cache = self.load_dicts(variant)
        if 'global_dict' in cache:
            global_dict = cache['global_dict'][1]
        else:
            global_dict = self.default_cache()

        replace = {}

        for key in cache:
            if key != 'global_dict':
                for word in cache[key][1]:
                    replace.setdefault( (word, cache[key][1][word]), 0)
                    replace[(word, cache[key][1][word])] += 1

        replace = [ (replace[key], key[0], key[1]) for key in replace ]

        replace.sort(reverse = True)

        for data in replace:
            if data[0] >= 5:
                print data[1].encode('utf-8'), data[2].encode('utf-8'), data[0]

    def optimize_all_global_dict(self):
        for variant in self.variants:
            self.optimize_global_dict_variant(variant)

    def check_title_variant(self, variant, title):
        cache = self.load_dicts(variant)
        page = self.get_page(title)

        try:
            last_rev = page.latestRevision()
        except pywikibot.exceptions.NoPage:
            print 'Page does not exist'
            return

        if last_rev in cache:
            print 'Found'
            local_dict = cache[last_rev][1]
            print local_dict
            if 'global_dict' in cache:
                global_dict = cache['global_dict'][1]
            else:
                global_dict = collection.OrderedDict()

            redundant_words = self.get_dict_redundancy(global_dict, local_dict)
            self.dump_redundant_words(title, redundant_words)
        else:
            print 'Not found'

    def check_title(self, title):
        for variant in self.variants:
            self.check_title_variant(variant, title)

    def check_cache(self, title, local_dict, global_dict):
        redundant_words = self.get_dict_redundancy(global_dict, local_dict)
        self.dump_redundant_words(title, redundant_words)

    def check_all_title_variant(self, variant):
        cache = self.load_dicts(variant)
        if 'global_dict' in cache:
            global_dict = cache['global_dict'][1]
        else:
            global_dict = self.default_cache()

        for key in cache:
           if key != 'global_dict':
                self.check_cache(cache[key][0], cache[key][1], global_dict)

    def check_all(self):
        for variant in self.variants:
                self.check_all_title_variant(variant)

    def check_useless_dict_entry(self, variant):
        cache = self.load_dicts(variant)
        transform = [ x[0] for x in self.config[variant]['transform'] ]
        regex = u'(' + u'|'.join(transform) + u')'
        for key in cache:
            local_dict = cache[key][1]
            for word in local_dict:
                if re.search(regex, word) or re.search(regex, local_dict[word]):
                    if type(cache[key][0]) == type(3):
                        print 'global_dict'
                    else:
                        print cache[key][0].encode('utf-8')
                    self.dump_dict_entry(word, local_dict)

    def get_useless_char(self):
        for variant in self.variants:
            if len(self.config[variant]['transform']):
                self.check_useless_dict_entry(variant)

    def find_words(self, words, local_dict, global_dict):
        if local_dict.has_key(words):
            return local_dict[words], False
        if global_dict.has_key(words):
            return global_dict[words], True
        return None, None

    # This mimic code at:
    # https://wikisource.org/wiki/User:Helder.wiki/Scripts/LanguageConverter.js
    def find_repl(self, words_list, i, local_dict, global_dict):
        repl = None
        glb = None
        words = u''
        for num in range(self.max_seq, 0, -1):
            if i + num >= len(words_list):
                continue

            words = u' '.join(words_list[i:i + num])

            repl, glb = self.find_words(words, local_dict, global_dict)

            if not repl:
                sub_w = words.lower()
                sup_w = words.upper()
                first_sup_w = words[0].upper() + words[1:]
                if sup_w == words:
                    repl, glb = self.find_words(first_sup_w,
                                                local_dict, global_dict)
                    if repl and not glb:
                        words = first_sup_w

                    if not repl:
                        repl, glb = self.find_words(sub_w, local_dict,
                                                    global_dict)
                        if repl and not glb:
                            words = sub_w
                elif first_sup_w == words:
                    repl, glb = self.find_words(sub_w, local_dict,
                                                global_dict)
                    if repl and not glb:
                        words = sub_w
            if repl:
                break

        return repl, glb, words, num

    def suggest_dict(self, title):
        p = self.get_page(title)
        html = self.get_html(p)

        new_html = common_html.get_head(u'TITLE') + u"\n<body>"  + html + u'\n</body>\n</html>'
        root = etree.fromstring(new_html.encode('utf-8'))

        exclude = set()

        for variant in self.variants:
            html_id = self.config[variant]['modernize_div_id']

            for it in root.findall(".//{http://www.w3.org/1999/xhtml}div[@id='%s']" % html_id):
                exclude.add(it)

        html_text = self.get_etree_text(root, exclude)

        # result = {
        # 'variant_name_1' : {
        #    'local_dict_used' : [(A, B), ... ],
        #    'suggest_local_dict' : { 'C' : 'D' ... },
        #    'speller_suggest' : [ ( 'E', [ 'G', 'H', ]), ... ]
        #    }
        # 'variant_name_2' : { ... }
        # }
        result = {}

        for variant in self.variants:
            speller = spell.Speller(self.config[variant]['aspell_lang'])
            cache = self.load_dicts(variant)
            if 'global_dict' in cache:
                global_dict = cache['global_dict'][1]
            else:
                global_dict = []

            other_local_dict = {}
            for key in cache:
                if key != 'global_dict':
                    d = cache[key][1]
                    for words in d:
                        other_local_dict[words] = d[words]


            local_dict = self.parse_local_dict(variant, html)

            text = html_text

            for d in self.config[variant]['transform']:
                text = re.sub(d[0], d[1], text)

            # set of entry used in the local dict, a set because we want
            # to keep the order in local_dict so we don't store here the repl
            # string but we will iter the ordered local_dict and check
            # if a word is present in this set.
            used_local_dict = set()
            # map of entry used in all other local dict, good suggestion to
            # give to user
            suggest_local_dict = {}
            # all other words, these will be check spelled to provide an
            # additionnal set of suggestion
            word_seen = set()

            regex_split = re.compile(u'([' + self.word_chars + u']+)')
            words_list = regex_split.findall(text)
            i = 0
            while True:
                if i >= len(words_list):
                    break

                repl, glb, new_words, num = self.find_repl(words_list, i,
                                                           local_dict,
                                                           global_dict)

                if repl:
                    if not glb:
                        used_local_dict.add(new_words)
                else:
                    # not found in global or local dict, try in all other
                    # local dict to get suggestion.
                    repl, glb, new_words, num = self.find_repl(words_list, i,
                                                           other_local_dict,
                                                           {})
                    if repl:
                        suggest_local_dict[new_words] = repl

                if not repl:
                    word_seen.add(words_list[i])
                    i += 1
                else:
                    i += num

            word_seen = [x for x in word_seen if not speller.check(x)]
            speller_suggest = [(x, speller.suggest(x)[:5]) for x in word_seen]

            # local dict is an ordered dict, so we can put words in the same
            # order as the local_dict, this allow better wiki diff when a local
            # dict is updated.
            local_dict_used = [ (x, local_dict[x]) for x in local_dict if x in used_local_dict ]

            # FIXME: for suggest_local_dict, must we remove suggested words
            # from other local dict but working word for the check speller?

            result[variant] = {}
            result[variant]['local_dict_used'] = local_dict_used
            result[variant]['suggest_local_dict'] = suggest_local_dict
            result[variant]['speller_suggest'] = speller_suggest

        return result

    def locate_dict(self, variant, word):
        cache = self.load_dicts(variant)
        for key in cache:
            if cache[key][1].has_key(word):
                if type(cache[key][0]) == type(3):
                    print 'global_dict'
                else:
                    print cache[key][0].encode('utf-8')

    def locate_all_dict(self, word):
        for variant in self.variants:
            self.locate_dict(variant, word)

    def load_text(self, p, variant):
        filename = self.cache_dir + self.lang + '/' + str(p.latestRevision())

        if not os.path.exists(filename):
            html = self.get_html(p)
            new_html = common_html.get_head(u'TITLE') + u"\n<body>"  + html + u'\n</body>\n</html>'
            root = etree.fromstring(new_html.encode('utf-8'))
            exclude = set()
            html_id = self.config[variant]['modernize_div_id']

            for it in root.findall(".//{http://www.w3.org/1999/xhtml}div[@id='%s']" % html_id):
                exclude.add(it)

            text = self.get_etree_text(root, exclude)
            for d in self.config[variant]['transform']:
                text = re.sub(d[0], d[1], text)

            utils.write_file(filename, text)
        else:
            text = utils.read_file(filename)

        return text

    def locate_all_html(self, word):
        for variant in self.variants:
            cache  = self.load_dicts(variant)
            for p in self.get_local_dict_list(variant):
                text = self.load_text(p, variant)

                regex_split = re.compile(u'([' + self.word_chars + u']+)')
                words_list = regex_split.findall(text)

                if p.latestRevision() in cache and word in cache[p.latestRevision()][1]:
                    continue

                local_dict = { word : u'repl' }
                i = 0
                while True:
                    if i >= len(words_list):
                        break
                    repl, glb, new_words, num = self.find_repl(words_list, i,
                                                               local_dict,
                                                               {})

                    if repl:
                        print p.title().encode('utf-8')
                        break
                    else:
                        i += 1

            # No need to iterate over all variant as the html does not depend
            # on the variant.
            break

    def useless_dict_entry_variant(self, variant):
        cache = self.load_dicts(variant)
        for p in self.get_local_dict_list(variant):
            if p.latestRevision() in cache:
                text = self.load_text(p, variant)
                regex_split = re.compile(u'([' + self.word_chars + u']+)')
                words_list = regex_split.findall(text)
                local_dict = cache[p.latestRevision()][1]
                used_word = set()

                #print text.encode('utf-8')

                i = 0
                while True:
                    if i >= len(words_list):
                        break

                    repl, glb, new_words, num = self.find_repl(words_list, i,
                                                               local_dict,
                                                               {})

                    if repl:
                        used_word.add(new_words)
                        i += num
                    else:
                        i += 1

                first = True
                for key in local_dict:
                    if not key in used_word:
                        if first:
                            print cache[p.latestRevision()][0].encode('utf-8')
                            first = False
                        print '* ' + key.encode('utf-8')

    def useless_dict_entry(self):
        for variant in self.variants:
            self.useless_dict_entry_variant(variant)

    def test_global_dict(self, variant):
        p = self.get_global_dict(variant)
        html = self.get_html(p)
        result = self.parse_global_dict(html)
        for key in result:
            print key.encode('utf-8'), result[key].encode('utf-8')

    def test_suggest_dict(self, title):
        result = self.suggest_dict(title)
        for variant in result:
            print variant
            for key in result[variant]:
                print key, result[variant][key]

    def test_global_dict_config(self):
        for variant in self.variants:
            self.test_global_dict(variant)

    def test_local_dict_config(self):
        for variant in self.variants:
            for p in self.get_local_dict_list(variant):
                print p.latestRevision()

    def test_cache(self, variant):
        cache = self.load_dicts(variant)
        self.save_dicts(variant, cache)

    def test_cache_config(self):
        for variant in self.variants:
            self.test_cache(variant)


if __name__ == '__main__':
    lang = None
    title = None
    cmd = None
    word = None
    for arg in sys.argv[1:]:
        if arg.startswith('-lang:'):
            lang = arg[len('-lang:'):]
        elif arg.startswith('-cmd:'):
            cmd = arg[len('-cmd:'):]
        elif arg.startswith('-title:'):
            title = unicode(arg[len('-title:'):], 'utf-8')
        elif arg.startswith('-word:'):
            word = unicode(arg[len('-word:'):], 'utf-8')
        else:
            print >> sys.stderr, "unknown arg:", arg
            exit(1)

    modernization = Modernization(lang)
        
    if cmd == 'test':
        modernization.test_global_dict_config()
        modernization.test_local_dict_config()
        modernization.test_cache_config()
    elif cmd == 'update':
        modernization.update_cache()
    elif cmd == 'check_title':
        modernization.check_title(title)
    elif cmd == 'check_all':
        modernization.check_all()
    elif cmd == 'optimize_local_dict':
        modernization.optimize_all_local_dict()
    elif cmd == 'optimize_global_dict':
        modernization.optimize_all_global_dict()
    elif cmd == 'useless_char':
        modernization.get_useless_char()
    elif cmd == 'suggest':
        modernization.test_suggest_dict(title)
    elif cmd == 'find_in_dict':
        modernization.locate_all_dict(word)
    elif cmd == 'find_in_html':
        modernization.locate_all_html(word)
    elif cmd == 'useless_dict_entry':
        modernization.useless_dict_entry()
    else:
        print "unknown -cmd:", cmd
