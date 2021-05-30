#!/usr/bin/python
# GPL V2, author phe                                                            
import pywikibot
from pywikibot.data import api
import time
import re
import types
import utils
import sys


def site_matrix():
    req = api.Request(site=pywikibot.Site('meta', 'meta'), action='sitematrix')
    data = req.submit()
    return data['sitematrix']


def proofread_info(lang):
    req = api.Request(site=pywikibot.getSite(lang, 'wikisource'),
                      action='query', meta='proofreadinfo')
    data = req.submit()
    return data['query']


def get_all_lang(family):
    results = []
    all_sites = site_matrix()
    for lang in all_sites:
        if type(all_sites[lang]) is dict:
            for site in all_sites[lang]['site']:
                code = all_sites[lang]['code']
                if site['code'] == family and not 'closed' in site:
                    results.append(code)

    results.sort()
    return results


def safe_put(page, text, comment):
    if re.match("^[\s\n]*$", text):
        return

    max_retry = 5

    retry_count = 0
    while retry_count < max_retry:
        retry_count += 1
        try:
            page.put(text, comment=comment)
            break
        except pywikibot.LockedPage:
            print >> sys.stderr, "put error : Page %s is locked?!" % page.title(asUrl=True).encode("utf8")
            utils.print_traceback()
            break
        except pywikibot.NoPage:
            print >> sys.stderr, "put error : Page does not exist %s" % page.title(asUrl=True).encode("utf8")
            utils.print_traceback()
            break
        except pywikibot.NoUsername:
            print >> sys.stderr, "put error : No user name on wiki %s" % page.title(asUrl=True).encode("utf8")
            utils.print_traceback()
            break
        except pywikibot.PageNotSaved:
            print >> sys.stderr, "put error : Page not saved %s" % page.title(asUrl=True).encode("utf8")
            print >> sys.stderr, "text len: ", len(text)
            utils.print_traceback()
            print >> sys.stderr, "sleeping for:", 10 * retry_count
            time.sleep(10 * retry_count)
            continue
        except pywikibot.OtherPageSaveError:
            # this can occur for read-only DB because slave lag, so retry
            # a few time
            print >> sys.stderr, "put error : Page not saved %s" % page.title(asUrl=True).encode("utf8")
            print >> sys.stderr, "retrying in", retry_count, "minute(s)"
            time.sleep(retry_count * 60)
            continue
        except:
            print >> sys.stderr, "put error: unknown exception"
            utils.print_traceback()
            time.sleep(10)
            break

    if retry_count >= max_retry:
        print >> sys.stderr, "unable to save page after", max_retry, "try, bailing out"
        pass
