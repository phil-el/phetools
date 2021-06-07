import os
import sys
import pywikibot
from common import pywikibot_utils


def gen_lang(dict_name, result):
    for family in dict_name:
        for lang in dict_name[family]:
            result.add(lang)


def gen_all_lang():
    result = set()

    for lang in pywikibot_utils.get_all_lang('wikisource'):
        result.add(lang)

    return result


def name_from_ns(namespaces, ns):
    return namespaces[ns].custom_name


def gen_namespace(lang):
    site = pywikibot.Site(lang, 'wikisource')
    text = 'namespaces["wikisource"]["%s"] = {\n' % lang

    namespaces = site.namespaces()
    for ns in namespaces:
        for name in namespaces[ns]:
            if name:
                text += '    "%s" : %s,\n' % (name, ns)
    text += '}\n'

    data = pywikibot_utils.proofread_info(lang)['proofreadnamespaces']

    text += 'index["wikisource"]["%s"] = "%s"\n' % (lang, name_from_ns(namespaces, data['index']['id']))
    text += 'page["wikisource"]["%s"] = "%s"\n' % (lang, name_from_ns(namespaces, data['page']['id']))

    return text


def gen_namespace_old():
    return """

namespaces["wikisource"]["old"] = {
    "Talk" : 1,
    "User" : 2,
    "User talk" : 3,
    "Wikisource" : 4,
    "Project" : 4,
    "WS" : 4,
    "Wikisource talk" : 5,
    "Project talk" : 5,
    "WT" : 5,
    "File" : 6,
    "Image" : 6,
    "File talk" : 7,
    "Image talk" : 7,
    "MediaWiki" : 8,
    "MediaWiki talk" : 9,
    "Template" : 10,
    "Template talk" : 11,
    "Help" : 12,
    "Help talk" : 13,
    "Category" : 14,
    "Category talk" : 15,
    "Author" : 108,
    "Author talk" : 109,
    "Page" : 104,
    "Page talk" : 105,
    "Index" : 106,
    "Index talk" : 107,
    "Media" : -2,
    "Special" : -1,
}
index["wikisource"]["old"] = "Index"
page["wikisource"]["old"] = "Page"

"""


def gen_all_namespace(langs):
    text = '# -*- coding: utf-8 -*-\n'
    text += '# auto-generated by %s, do not edit manually.\n\n' % sys.argv[0]

    text += "namespaces = {}\n"
    # FIXME: not really correct, works only for wikisource atm, no big deal
    text += 'namespaces["wikisource"] = {}\n\n'

    text += 'index = {}\n'
    text += 'index["wikisource"] = {}\n\n'

    text += 'page = {}\n'
    text += 'page["wikisource"] = {}\n\n'

    for lang in langs:
        text += gen_namespace(lang)

    text += gen_namespace_old()
    return text


if __name__ == "__main__":
    langs = gen_all_lang()
    text = gen_all_namespace(langs)

    target = os.path.expanduser('~/wikisource/ws_namespaces.py')
    old_text = ''
    if os.path.exists(target):
        fd = open(target, 'r')
        old_text = fd.read()
        fd.close()
    if old_text != text:
        print("writing file, match and split server needs a restart")
        fd = open(target, 'w')
        fd.write(text)
        fd.close()
