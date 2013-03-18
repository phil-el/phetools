#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import resource
import utils

tesseract_languages = {
        'fr':"fra",
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

tesseract_path = '/home/phe/bin/tesseract'

def setrlimits():
    resource.setrlimit(resource.RLIMIT_AS, (1<<30, 1<<30))
    resource.setrlimit(resource.RLIMIT_CORE, (1<<27, 1<<27))
    resource.setrlimit(resource.RLIMIT_CPU, (30*60, 30*60))

def ocr(filename, out_basename, lang, config = ''):
    stderr = open("/home/phe/wsbot/log/tesseract.log", "a")
    env = { "TESSDATA_PREFIX" : '/home/phe/share'}
    ls = subprocess.Popen([ tesseract_path, filename, out_basename, "-l", lang, config], stdout=subprocess.PIPE, stderr=stderr, preexec_fn=setrlimits, close_fds = True, env = env)
    text = utils.safe_read(ls.stdout)
    if text:
        print text
    ls.wait()
    stderr.close()
    if ls.returncode != 0:
        print >> sys.stderr, "ocr.ocr() fail to exec tesseract:", ls.returncode
        return None

    # FIXME: this is silly ?
    try:
        fd = open(out_basename + ".txt")
        txt = fd.read()
        fd.close()
    except:
        txt = None
    return txt
