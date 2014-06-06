#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
sys.path.append('/data/project/phetools/phe/common')
import os
import subprocess
import resource
import utils
import sys

tesseract_languages = {
        'bn':'ben',
        'fr':"fra",
        'he': 'heb',
        'en':"eng",
        'de':"deu",
        'de-f':"deu-frak",
        'la':"ita",
        'is':'isl', # needs tess 3.02
        'it':"ita",
        'es':"spa",
        'pt':"spa",
        'ru':"rus",
        }

tesseract_path = 'tesseract'

def ocr(filename, out_basename, lang, config = ''):
    stderr = open("/data/project/phetools/log/tesseract.err", "a")
    ls = subprocess.Popen([ tesseract_path, filename, out_basename, "-l", lang, config], stdout=subprocess.PIPE, stderr=stderr, close_fds = True)
    text = utils.safe_read(ls.stdout)
    if text:
        print text,
    ls.wait()
    stderr.close()
    if ls.returncode != 0:
        print >> sys.stderr, "ocr.ocr() fail to exec tesseract:", ls.returncode
        return None

    try:
        fd = open(out_basename + ".txt")
        txt = fd.read()
        fd.close()
    except:
        txt = None
    return txt

if __name__ == "__main__":
    import os
    image_filename = 'temp.jpg'
    url= 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Petitot_-_Collection_compl%C3%A8te_des_m%C3%A9moires_relatifs_%C3%A0_l%E2%80%99histoire_de_France%2C_2e_s%C3%A9rie%2C_tome_45.djvu/page280-1024px-Petitot_-_Collection_compl%C3%A8te_des_m%C3%A9moires_relatifs_%C3%A0_l%E2%80%99histoire_de_France%2C_2e_s%C3%A9rie%2C_tome_45.djvu.jpg'
    lang = 'fr'
    utils.copy_file_from_url(url, image_filename)
    print ocr(image_filename, image_filename, tesseract_languages[lang])

    os.remove(image_filename)
    os.remove(image_filename + ".txt")
