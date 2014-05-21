#!/usr/bin/python
# GPL V2, author phe                                                            
import pywikibot
import time
import re

def safe_put(page, text, comment):
    if re.match("^[\s\n]*$", text):
        return

    while 1:
        try:
            page.put(text, comment = comment)
            break
        except pywikibot.LockedPage:
            print "put error : Page %s is locked?!" % page.title(asUrl=True).encode("utf8")
            break
        except pywikibot.NoPage:
            print "put error : Page does not exist %s" % page.title(asUrl=True).encode("utf8")
            break
        except pywikibot.NoUsername:
            print "put error : No user name on wiki %s" % page.title(asUrl=True).encode("utf8")
            break
        except pywikibot.PageNotSaved:
            print "put error : Page not saved %s" % page.title(asUrl=True).encode("utf8") 
            print "text len: ", len(text)
            break
        except:
            print "put error: unknown exception"
            time.sleep(5)
            break
