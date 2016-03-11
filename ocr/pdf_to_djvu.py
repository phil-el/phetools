# -*- coding: utf-8 -*-
#
# @file pdf_to_djvu.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import subprocess
import resource
import os
import sys
import tempfile
import xml.etree.ElementTree as etree
import urllib
import json
import utils
import shutil

djvulibre_path = ''
gsdjvu = os.path.expanduser('~/root/gsdjvu/bin/gs')

def setrlimits():
    mega = 1 << 20
    resource.setrlimit(resource.RLIMIT_AS, (1536*mega, 1536*mega))
    resource.setrlimit(resource.RLIMIT_CORE, (128*mega, 128*mega))
    resource.setrlimit(resource.RLIMIT_CPU, (5*60*60, 5*60*60))

def exec_process(args):
    ls = subprocess.Popen(args, stdout=subprocess.PIPE, preexec_fn=setrlimits,
                          close_fds = True)
    text = ls.stdout.read()
    ls.wait()
    if ls.returncode != 0:
        print >> sys.stderr, "process fail: ", ls.returncode, args
        # FIXME: raise something and fix caller
        return None
    return text

def pdf_to_djvu(in_file):

    if type(in_file) == type(u''):
        in_file = in_file.encode('utf-8')

    if gsdjvu:
        os.environ['GSDJVU'] = gsdjvu

    out_file = in_file[:-3] + 'djvu'

    # --words option is useless as djvudigital fails to extract text layer
    # from many pdf. I've not yet see a pdf where djvudigital is able
    # to extract text layer and anyway it is likely to do the same inaccurate
    # text extraction as pdftotext.
    args = [ djvulibre_path + 'djvudigital',  "--dpi=300", in_file, out_file ]
    text = exec_process(args)
    if text:
        print text
    else:
        out_file = None

    if gsdjvu:
        del os.environ['GSDJVU']

    return out_file

def quote_text_for_djvu(text):
    new_text = text

    # Some tools has trouble with (" and ") in text layer as they are also
    # used to mark begin/end of pages, we scratch them as they are very rare
    # anyway
    new_text = new_text.replace('("',  '( ')
    new_text = new_text.replace('")',  ' )')
    new_text = new_text.replace('( "', '( ')
    new_text = new_text.replace('" )', ' )')

    new_text = new_text.replace('\\', '\\\\')
    new_text = new_text.replace('"',  '\\"')
    new_text = new_text.replace('\n', '\\n')
    new_text = new_text.replace('\r', '\\r')

    return '"' + new_text + '"'

def write_page_text(page, text):
    new_text = quote_text_for_djvu(text)
    # text coordinate are fake atm
    new_text = '(page 0 0 1 1 ' + new_text + ')'
    temp_filename = 'page_%04d.temp.txt' % page
    fd = open(temp_filename, 'w')
    fd.write(new_text)
    fd.close()

def add_text_layer(nr_pages, out_file):
    args = [ 'djvused', out_file, '-e' ]

    cmdline = ''
    for page in range(1, nr_pages + 1):
        temp_filename = 'page_%04d.temp.txt' % page
        cmdline += 'select %d; set-txt ' % page + temp_filename + '; '

    cmdline += 'save;'

    args += [ cmdline ]

    text = exec_process(args)
    if text:
        print text
        print "JOB DONE"
        return True
    else:
        return False

def read_pdf_text(in_file):
    args = [ 'pdftotext', '%s' % in_file, '-' ]
    text = exec_process(args)
    if text == None:
        return None
    text = text.split('')
    # pdftotext end the last page with a  marker, remove it
    text = text[:-1]

    for r in range(1, len(text) + 1):
        fd = open('page_%04d.txt' % r, 'w')
        fd.write(text[r - 1])
        fd.close()

    return len(text)

# This use pdftotext but result are not really accurate ;(
# pdftotext tends to add way too much line feed if the
# baseline of words are not exactly identical on the same line
def pdf_text_to_djvu(in_file, out_file):
    nr_pages = read_pdf_text(in_file)
    if not nr_pages:
        return

    print "NR PAGES", nr_pages

    for page in range(1, nr_pages + 1):
        write_page_text(page, text)
        text_filename = 'page_%04d.txt' % page
        fd = open(text_filename)
        text = fd.read()
        fd.close()
        write_page(page, text)

    ret = add_text_layer(nr_pages, out_file)

    for r in range(1, nr_pages + 1):
        os.remove('page_%04d.txt' % r)
        os.remove('page_%04d.temp.txt' % r)

    return ret

def pdf_with_text_layer_to_djvu(in_file):
    temp_dir = tempfile.mkdtemp()
    print "temp_dir", temp_dir
    os.chdir(temp_dir)

    out_file = pdf_to_djvu(in_file)
    print out_file
    if out_file:
        pdf_text_to_djvu(in_file, out_file)
    os.rmdir(temp_dir)
    print out_file

def get_deep_text(element):
    text = element.text or ''
    for subelement in element:
        text += get_deep_text(subelement)
    text += element.tail or ''
    return text[:-1] + ' '

# This is much more accurate than using pdftotext
def pdf_text_to_djvu_with_xml(xml_file, out_file):
    fd = open(xml_file)
    last_text = ''
    page_nr = 1
    for event, elem in etree.iterparse(fd):
        if event == 'end':
            if elem.tag.lower() == 'line':
                last_text += get_deep_text(elem)
            elif elem.tag.lower() == 'paragraph':
                last_text += '\n'
            elif elem.tag.lower() == 'object':
                write_page_text(page_nr, last_text.encode('utf-8'))
                page_nr += 1
                last_text = ''
                elem.clear()
    fd.close()

    ret_code = add_text_layer(page_nr - 1, out_file)

    for r in range(1, page_nr):
        os.remove('page_%04d.temp.txt' % r)

def get_ia_files(ia_id):
    result = {
        'pdf' : None,
        'xml' : None
    }

    url = 'https://archive.org/metadata/' + ia_id + '/files'
    fd = urllib.urlopen(url)
    data = json.loads(fd.read())
    fd.close()
    for d in data['result']:
        # this one exists in old and new items
        if d['format'] == 'Djvu XML':
            result['xml'] = { 'name' : d['name'], 'sha1' : d['sha1'] }
        # 'Additional Text PDF' format exists only in new items but in old
        # items the .djvu must exist and should be used directly. For older
        # item format is "Text PDF".
        #
        # FIXME: try an old item with derivation redone which delete the djvu
        # to check if 'Additional Text PDF' is created in such case else we
        # will need to falback to format = 'Text PDF' if 'Additional Text PDF'
        # doesn't exist.
        elif d['format'] == 'Additional Text PDF':
            result['pdf'] = { 'name' : d['name'], 'sha1' : d['sha1'] }
    return result

def copy_ia_file(ia_id, metadata):
    base_url = 'https://archive.org/download/%s/' % ia_id

    utils.copy_file_from_url(base_url + metadata['name'], metadata['name'],
                             expect_sha1 = metadata['sha1'])

# externally visible through an api
def pdf_to_djvu_from_ia(ia_id):
    temp_dir = tempfile.mkdtemp()
    print "temp_dir", temp_dir
    os.chdir(temp_dir)

    files = get_ia_files(ia_id)

    copy_ia_file(ia_id, files['pdf'])
    copy_ia_file(ia_id, files['xml'])

    djvu_name = pdf_to_djvu(files['pdf']['name'])
    if djvu_name:
        pdf_text_to_djvu_with_xml(files['xml']['name'], djvu_name)
        shutil.move(djvu_name, os.path.expanduser('~/cache/ia_pdf/'))

    os.remove(files['pdf']['name'])
    os.remove(files['xml']['name'])

    os.rmdir(temp_dir)

    return True if djvu_name else False


if __name__ == "__main__":
    pdf_to_djvu_from_ia('BourgetLEcuyere1921')
