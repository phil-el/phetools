import sys
import re
import xml.etree.ElementTree as etree
import subprocess
import os
import resource
from common import utils

djvulibre_path = ''
djvutoxml = djvulibre_path + 'djvutoxml'
djvutxt = djvulibre_path + 'djvutxt'

converter = "djvu_text_to_hocr 0.00.00"

# All of these contain the needed indentation and line feed

hocr_begin = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name='ocr-system' content='%s' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
 </head>
 <body>
""" % converter

hocr_end = """ </body>
</html>
"""

# for now it's sufficient to give page id = 1 and physical page = 0 as
# we do the output as separate page.
hocr_page_begin = """  <div class='ocr_page' id='page_%(logical_page_id)d' title='image "%(image_title)s"; bbox %(page_bbox)s; ppageno %(physical_page_id)d'>
"""

hocr_page_end = """  </div>
"""

# carea are called PAGECOLUMN in xml output
hocr_carea_begin = """   <div class='ocr_carea' id='block_%(column_id)d_%(column_id)d' title="bbox %(column_bbox)s">
"""
hocr_carea_end = """   </div>
"""

hocr_para_begin = """    <p class='ocr_par' dir='ltr' id='par_%(para_id)d' title="bbox %(para_bbox)s">
"""

hocr_para_end = """    </p>
"""

hocr_line_begin = """     <span class='ocr_line' id='line_%(line_id)d' title="bbox %(line_bbox)s">"""

hocr_line_end = """
     </span>
"""

hocr_word_begin = """<span class='ocrx_word' id='word_%(word_id)d' title="bbox %(word_bbox)s">"""

hocr_word_end = """</span> """


class Bbox:
    def __init__(self, x1=None, y1=None, x2=None, y2=None):
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2

    # coord are top-down according to the doc, but words coord are in
    # x1, y2, x2, y1 order.
    def init(self, init_str):
        init_str = init_str.split(',')
        self.x1 = int(init_str[0])
        self.y1 = int(init_str[3])
        self.x2 = int(init_str[2])
        self.y2 = int(init_str[1])

    def __ior__(self, other):
        self.x1 = min(self.x1, other.x1)
        self.y1 = min(self.y1, other.y1)
        self.x2 = max(self.x2, other.x2)
        self.y2 = max(self.y2, other.y2)
        return self

    # compatible with hocr bbox string
    def __str__(self):
        return str(self.x1) + " " + str(self.y1) + " " + str(self.x2) + " " + str(self.y2)


class OcrPage:
    def __init__(self):
        self.page_buffer = ''
        self.logical_page_id = 1
        self.physical_page_id = 0

    def add_param(self, e):
        if e.attrib.get('name', '') == 'PAGE':
            self.page_name = e.attrib['value']

    def grow_bbox(self, bbox1, bbox2):
        bbox1 |= bbox2

    def start_page(self, e):
        self.width = int(e.attrib['width'])
        self.height = int(e.attrib['height'])
        self.page_name = ''
        self.column_box = Bbox(self.width, self.height, 0, 0)
        self.region_box = Bbox(self.width, self.height, 0, 0)
        self.para_box = Bbox(self.width, self.height, 0, 0)
        self.line_box = Bbox(self.width, self.height, 0, 0)
        self.word_box = Bbox(self.width, self.height, 0, 0)
        self.char_box = Bbox(self.width, self.height, 0, 0)
        self.column_id = 1
        self.region_id = 1
        self.para_id = 1
        self.line_id = 1
        self.word_id = 1
        self.column_buffer = ''

    def end_page(self, e):
        data = {
            'page_bbox': '0 0 %d %d' % (self.width, self.height),
            'image_title': self.page_name,
            'logical_page_id': self.logical_page_id,
            'physical_page_id': self.physical_page_id
        }
        self.page_buffer += hocr_page_begin % data + self.column_buffer + hocr_page_end
        self.logical_page_id += 1
        self.physical_page_id += 1

    def start_column(self, e):
        self.para_buffer = ''
        self.column_box = Bbox(self.width, self.height, 0, 0)
        if 'coords' in e.attrib:
            self.column_box.init(e.attrib['coords'])

    def end_column(self, e):
        data = {
            'column_bbox': str(self.column_box),
            'column_id': self.column_id
        }
        self.column_buffer += hocr_carea_begin % data + self.para_buffer + hocr_carea_end
        self.column_id += 1

    # We ignore region in output and use column as ocr_carea
    def start_region(self, e):
        self.region_box = Bbox(self.width, self.height, 0, 0)
        if 'coords' in e.attrib:
            self.region_box.init(e.attrib['coords'])

    def end_region(self, e):
        self.grow_bbox(self.column_box, self.region_box)
        if 'coords' in e.attrib:
            self.region_box.init(e.attrib['coords'])
        self.region_id += 1

    def start_para(self, e):
        self.line_buffer = ''
        self.para_box = Bbox(self.width, self.height, 0, 0)
        if 'coords' in e.attrib:
            self.para_box.init(e.attrib['coords'])

    def end_para(self, e):
        self.grow_bbox(self.region_box, self.para_box)
        self.grow_bbox(self.column_box, self.para_box)
        data = {
            'para_bbox': str(self.para_box),
            'para_id': self.para_id
        }
        self.para_buffer += hocr_para_begin % data + self.line_buffer + hocr_para_end
        self.para_id += 1

    def start_line(self, e):
        self.word_buffer = ''
        self.line_box = Bbox(self.width, self.height, 0, 0)
        if 'coords' in e.attrib:
            self.line_box.init(e.attrib['coords'])

    def end_line(self, e):
        self.grow_bbox(self.para_box, self.line_box)
        self.grow_bbox(self.region_box, self.line_box)
        self.grow_bbox(self.column_box, self.line_box)
        data = {
            'line_bbox': str(self.line_box),
            'line_id': self.line_id
        }
        self.line_buffer += hocr_line_begin % data + self.word_buffer + hocr_line_end
        self.line_id += 1

    def start_word(self, e):
        self.word_text = e.text
        self.word_box = Bbox(self.width, self.height, 0, 0)
        if 'coords' in e.attrib:
            self.word_box.init(e.attrib['coords'])

    def end_word(self, e):
        self.grow_bbox(self.line_box, self.word_box)
        self.grow_bbox(self.para_box, self.word_box)
        self.grow_bbox(self.region_box, self.word_box)
        self.grow_bbox(self.column_box, self.word_box)
        # this can occur for empty words after input sanitization.
        if self.word_text != None:
            data = {
                'word_bbox': str(self.word_box),
                'word_id': self.word_id
            }
            self.word_buffer += hocr_word_begin % data + self.word_text + hocr_word_end
            self.word_id += 1

    def start_char(self, e):
        if self.word_text and e.text:
            self.word_text += e.text
        elif e.text:
            self.word_text = e.text
        self.char_box = Bbox(self.width, self.height, 0, 0)
        if 'coords' in e.attrib:
            self.char_box.init(e.attrib['coords'])

    def end_char(self, e):
        self.grow_bbox(self.word_box, self.char_box)
        self.grow_bbox(self.line_box, self.char_box)
        self.grow_bbox(self.para_box, self.char_box)
        self.grow_bbox(self.region_box, self.char_box)
        self.grow_bbox(self.column_box, self.char_box)

    def get_hocr_html(self):
        return hocr_begin + self.page_buffer + hocr_end

    def __str__(self):
        return str(self.width) + ' ' + str(self.height) + ' ' + self.page_name


# FIX a bug in djvutoxml, some control char are outside any tag and are
# invalid xml entity
class XmlFile:
    def __init__(self, source):
        if not hasattr(source, "read"):
            source = open(source, "rb")
        self.fd = source

    def read(self, size):
        text = self.fd.read(size)
        # Kludge... try to avoid cutting entity, assume no consecutive entity
        if "&" in text[-8:]:
            text += self.fd.read(8);

        # djvutoxml can produce invalid entity, just strip them.
        text = re.sub(r"&#\d+;", "", text)
        # bug in etree ?
        text = text.replace("&hl=", "")
        # Are text always in utf-8 ?
        # some djvu contains invalid sequence like (octal) \275 \276
        text = unicode(text, "utf-8", "replace")
        text = text.encode("utf-8")

        return text


def begin_elem(page, e):
    tag = e.tag.lower()
    if tag == 'param':
        page.add_param(e)
    elif tag == 'pagecolumn':
        page.start_column(e)
    elif tag == 'region':
        page.start_region(e)
    elif tag == 'paragraph':
        page.start_para(e)
    elif tag == 'line':
        page.start_line(e)
    elif tag == 'word':
        page.start_word(e)
    elif tag == 'char':
        page.start_char(e)
    else:
        print("unsuported tag", tag, file=sys.stderr)
        raise 'unsuported tag'


def end_elem(page, e):
    tag = e.tag.lower()
    if tag == 'param':
        page.add_param(e)
    elif tag == 'pagecolumn':
        page.end_column(e)
    elif tag == 'region':
        page.end_region(e)
    elif tag == 'paragraph':
        page.end_para(e)
    elif tag == 'line':
        page.end_line(e)
    elif tag == 'word':
        page.end_word(e)
    elif tag == 'char':
        page.end_char(e)
    else:
        print("unsuported tag", tag, file=sys.stderr)
        raise 'unsuported tag'


def parse_page_recursive(page, elem):
    for e in elem:
        begin_elem(page, e)
        parse_page_recursive(page, e)
        end_elem(page, e)


def parse_page(page, elem, page_nr):
    parse_page_recursive(page, elem)


def setrlimits():
    mega = 1 << 20
    resource.setrlimit(resource.RLIMIT_AS, (1024 * mega, 1024 * mega))
    resource.setrlimit(resource.RLIMIT_CORE, (128 * mega, 128 * mega))
    resource.setrlimit(resource.RLIMIT_CPU, (1 * 60 * 60, 1 * 60 * 60))


def do_parse(opt, filename):
    try:
        ls = subprocess.Popen([djvutoxml, filename], stdout=subprocess.PIPE, preexec_fn=setrlimits, close_fds=True)

        page_nr = 1
        for event, elem in etree.iterparse(XmlFile(ls.stdout)):
            if elem.tag.lower() == 'object':
                page = OcrPage()
                if not opt.silent:
                    print(page_nr, '\r', end=' ', file=sys.stderr)
                page.start_page(elem)
                parse_page(page, elem, page_nr)
                page.end_page(elem)

                filename = opt.out_dir + 'page_%04d.hocr' % page_nr

                if opt.compress:
                    text = page.get_hocr_html()
                    utils.compress_file_data(filename, text, opt.compress)
                else:
                    utils.write_file(filename, text)

                elem.clear()
                page_nr += 1

    finally:
        if not opt.silent:
            print('', file=sys.stderr)

        ls.stdout.read()
        ls.wait()

    return ls.returncode


def parse(opt, filename):
    try:
        ret_code = do_parse(opt, filename)
    except Exception:
        utils.print_traceback(filename)
        ret_code = -1

    return ret_code


def default_options():
    class Options:
        def __init__(self):
            self.compress = 'bzip2'
            self.out_dir = './'
            self.silent = False

    return Options()


# Kludgy.
def has_word_bbox(filename):
    ls = subprocess.Popen([djvutxt, filename, '--detail=word'], stdout=subprocess.PIPE, preexec_fn=setrlimits,
                          close_fds=True)
    for line in ls.stdout:
        if re.search(r'\(word \d+ \d+ \d+ \d+ ".*"', line):
            ls.kill()
            ls.wait()
            return True
    ls.wait()
    return False


if __name__ == "__main__":
    options = default_options()
    for arg in sys.argv[1:]:
        if arg == '-help':
            print(sys.argv[0], "-help -compress: -out_dir:dir -silent")
            sys.exit(1)
        elif arg.startswith('-compress:'):
            options.compress = arg[len('-compress'):]
        elif arg == '-silent':
            options.silent = True
        elif arg.startswith('-out_dir:'):
            if not arg.endswith('/'):
                arg += '/'
            options.out_dir = arg[len('-out_dir:'):]
        else:
            filename = arg

    if not os.path.exists(filename):
        print(f"file: {filename} doesn't exist")
        sys.exit(1)

    parse(options, filename)
