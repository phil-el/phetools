# -*- coding: utf-8 -*-

import re

def split_page_text(text):
    match = re.match(u'^(?ms)(<noinclude>.*?</noinclude>\s*)(.*)(\s*<noinclude>.*?</noinclude>)$', text)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return u'', text, u''

if __name__ == '__main__':
    pass
