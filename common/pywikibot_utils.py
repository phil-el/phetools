#!/usr/bin/python3
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
    if re.match(r"^[\s\n]*$", text):
        return

    max_retry = 5

    retry_count = 0
    while retry_count < max_retry:
        retry_count += 1
        title = page.title(asUrl=True)
        try:
            page.put(text, comment=comment)
            break
        except pywikibot.LockedPage:
            print(f"put error : Page", title, "is locked?!", file=sys.stderr)
            utils.print_traceback()
            break
        except pywikibot.NoPage:
            print("put error : Page does not exist", title, file=sys.stderr)
            utils.print_traceback()
            break
        except pywikibot.NoUsername:
            print("put error : No user name on wiki", title, file=sys.stderr)
            utils.print_traceback()
            break
        except pywikibot.PageSaveRelatedError:
            print("put error : Page not saved", title, file=sys.stderr)
            print("text len: ", len(text), file=sys.stderr)
            utils.print_traceback()
            print("sleeping for:", 10 * retry_count, file=sys.stderr)
            time.sleep(10 * retry_count)
            continue
        except pywikibot.OtherPageSaveError:
            # this can occur for read-only DB because slave lag, so retry
            # a few time
            print("put error : Page not saved", title, file=sys.stderr)
            print("retrying in", retry_count, "minute(s)", file=sys.stderr)
            time.sleep(retry_count * 60)
            continue
        except Exception as e:
            print("put error: unknown exception", e, file=sys.stderr)
            utils.print_traceback()
            time.sleep(10)
            break

    if retry_count >= max_retry:
        print("unable to save page after", max_retry, "try, bailing out", file=sys.stderr)
        pass
