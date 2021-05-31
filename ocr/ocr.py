#!/usr/bin/python

# FIXME: this script has the same name as it's container directory
# this is prone error as both "from ocr import ocr" and "import ocr"
# doen't trigger any assertion but have a different semantics.

import sys
import os
import subprocess
import resource
from common import utils

tesseract_languages = {
    'be': 'bel',
    'bn': 'ben',
    'ca': 'cat',
    'cs': 'ces',
    'da': 'dan',
    'de': 'deu',
    'de-f': 'deu-frak',
    'en': 'eng',
    'eo': 'epo',
    'es': 'spa',
    'et': 'est',
    'fr': 'fra',
    'he': 'heb',
    'hr': 'hrv',
    'hu': 'hun',
    'id': 'ind',
    'is': 'isl',
    'it': 'ita',
    'la': 'ita',
    'no': 'nor',
    'pl': 'pol',
    'pt': 'por',
    'ru': 'rus',
    'sv': 'swe',
    'ta': 'tam',
}

tesseract_path = 'tesseract'


def setrlimits():
    mega = 1 << 20
    resource.setrlimit(resource.RLIMIT_AS, (1536 * mega, 1536 * mega))
    resource.setrlimit(resource.RLIMIT_CORE, (128 * mega, 128 * mega))
    resource.setrlimit(resource.RLIMIT_CPU, (60 * 60, 60 * 60))


def ocr(filename, out_basename, lang, config=''):
    ls = subprocess.Popen([tesseract_path, filename, out_basename, "-l", lang, config], stdout=subprocess.PIPE,
                          preexec_fn=setrlimits, close_fds=True)
    text = utils.safe_read(ls.stdout)
    if text:
        print(text, end=' ')
    ls.wait()

    if config == '':
        out_filename = out_basename + ".txt"
    else:
        out_filename = out_basename + ".hocr"

    if not os.path.exists(out_filename) or ls.returncode:
        # in case returncode == 0
        print("ocr.ocr() fail to exec tesseract:", ls.returncode, filename, file=sys.stderr)

        fd = open(out_filename, 'w')
        fd.write('An error occurred during ocr processing: ' + filename)
        fd.close()

    fd = open(out_filename)
    txt = fd.read()
    fd.close()

    if ls.returncode != 0:
        print("ocr.ocr() fail to exec tesseract:", ls.returncode, filename, file=sys.stderr)
        return None

    return txt


if __name__ == "__main__":
    image_filename = 'temp.jpg'
    url = 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f4/Petitot_-_Collection_compl%C3%A8te_des_m%C3%A9moires_relatifs_%C3%A0_l%E2%80%99histoire_de_France%2C_2e_s%C3%A9rie%2C_tome_45.djvu/page280-1024px-Petitot_-_Collection_compl%C3%A8te_des_m%C3%A9moires_relatifs_%C3%A0_l%E2%80%99histoire_de_France%2C_2e_s%C3%A9rie%2C_tome_45.djvu.jpg'
    lang = 'fr'
    utils.copy_file_from_url(url, image_filename)
    print(ocr(image_filename, image_filename, tesseract_languages[lang], config='hocr'))

    os.remove(image_filename)
    os.remove(image_filename + ".txt")
