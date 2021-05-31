import re


def split_page_text(text):
    match = re.match(r'^(?ms)(<noinclude>.*?</noinclude>\s*)(.*)(\s*<noinclude>.*?</noinclude>)$', text)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return '', text, ''


if __name__ == '__main__':
    pass
