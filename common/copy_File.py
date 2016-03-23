# -*- coding: utf-8 -*-
#
# @file copy_File.py
#
# @remark Copyright 2016 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import utils
import pywikibot

def get_filepage(site, djvuname):
    try:
        page = pywikibot.page.FilePage(site, "File:" + djvuname)
    except pywikibot.NoPage:
        page = None

    if page:
        try:
            page.fileUrl()
        except:
            site = pywikibot.Site(code = 'commons', fam = 'commons')
            page = pywikibot.page.FilePage(site, "File:" + djvuname)

    return page

def copy_file(lang, family, filename, dest):
    site = pywikibot.getSite(lang, family)
    page = get_filepage(site, unicode(filename, 'utf-8'))
    url = page.fileUrl()
    utils.copy_file_from_url(url, dest, page.getFileSHA1Sum())

if __name__ == "__main__":
    import sys
    copy_file(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
