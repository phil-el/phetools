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

djvulibre_path = ''
gsdjvu = os.path.expanduser('~/root/gsdjvu/bin/gs')

def setrlimits():
    mega = 1 << 20
    resource.setrlimit(resource.RLIMIT_AS, (1536*mega, 1536*mega))
    resource.setrlimit(resource.RLIMIT_CORE, (128*mega, 128*mega))
    resource.setrlimit(resource.RLIMIT_CPU, (5*60*60, 5*60*60))

def pdf_to_djvu(in_file):

    if type(in_file) == type(u''):
        in_file = in_file.encode('utf-8')

    if gsdjvu:
        os.environ['GSDJVU'] = gsdjvu

    out_file = in_file[:-3] + 'djvu'

    djvudigital = djvulibre_path + 'djvudigital'
    # --words option is useless as many pdf contains text layer only for
    # the first page
    ls = subprocess.Popen([ djvudigital, "--dpi=300", in_file, out_file], stdout=subprocess.PIPE, preexec_fn=setrlimits, close_fds = True)
    text = ls.stdout.read()
    if text:
        print text
    ls.wait()
    if ls.returncode != 0:
        print >> sys.stderr, "djvudigital fail: ", ls.returncode, in_file
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

    ls = subprocess.Popen(args, stdout=subprocess.PIPE,
                          preexec_fn=setrlimits, close_fds = True)
    print ls.stdout.read()
    ls.wait()

    print "JOB DONE"

    return ls.returncode

def read_pdf_text(in_file):
    args = [ 'pdftotext', '%s' % in_file, '-' ]
    ls = subprocess.Popen(args, stdout=subprocess.PIPE,
                          preexec_fn=setrlimits, close_fds = True)
    text = ls.stdout.read()
    text = text.split('')
    # pdftotext end the last page with a  marker, remove it
    text = text[:-1]
    ls.wait()
    # FIXME: raise something ?
    if ls.returncode:
        print >> sys.stderr, "pdftotext fail:", ls.returncode
        return None

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

    ret_code = add_text_layer(nr_pages, out_file)

    for r in range(1, nr_pages + 1):
        os.remove('page_%04d.txt' % r)
        os.remove('page_%04d.temp.txt' % r)

    return ret_code

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

def get_deep_text( element ):
    text = element.text or ''
    for subelement in element:
        text += get_deep_text( subelement )
    text += element.tail or ''
    return text[:-1] + ' '

# This is much more accurate
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

def pdf_with_xml_layer_to_djvu(xml_file, out_file):
    temp_dir = tempfile.mkdtemp()
    print "temp_dir", temp_dir
    os.chdir(temp_dir)

    page_nr = pdf_text_to_djvu_with_xml(xml_file, out_file)

    os.rmdir(temp_dir)

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
        # this one exists only in new items but in the of old items the .djvu
        # must exist and should be used directly. For older item format is
        # "Text PDF".
        # FIXME: try an old item with derivation redone which delete the djvu
        # to check if 'Additional Text PDF' is created in such case.
        elif d['format'] == 'Additional Text PDF':
            result['pdf'] = { 'name' : d['name'], 'sha1' : d['sha1'] }
    return result

# externally visible through an api
def pdf_to_djvu_from_ia(ia_id):
    base_url = 'https://archive.org/download/%s/' % ia_id
    base_dir = os.path.expanduser('~/cache/ia_pdf/%s' % ia_id)

    files = get_ia_files(ia_id)

    pdf_name = base_dir + files['pdf']['name']
    xml_name = base_dir + files['xml']['name']

    print base_url  + files['pdf']['name']

    utils.copy_file_from_url(base_url + files['pdf']['name'], pdf_name,
                             expect_sha1 = files['pdf']['sha1'])
    utils.copy_file_from_url(base_url + files['xml']['name'], xml_name,
                             expect_sha1 = files['xml']['sha1'])

    djvu_name = pdf_to_djvu(pdf_name)
    if djvu_name:
        pdf_with_xml_layer_to_djvu(xml_name, djvu_name)

    os.remove(pdf_name)
    os.remove(xml_name)


if __name__ == "__main__":
    pdf_to_djvu_from_ia('BourgetLEcuyere1921')
