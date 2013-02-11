#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

def ocr(filename, out_basename, lang, config = ''):
    #os.putenv('LD_PRELOAD', '/opt/ts/lib/libtesseract_cutil.so.3') 
    #if lang in [ 'deu-frak', 'isl' ]:
    #    os.putenv('TESSDATA_PREFIX', '/home/phe/wsbot/')

    os.putenv('TESSDATA_PREFIX', '/home/phe/share')

    os.system("/home/phe/bin/tesseract %s %s -l %s %s 2>>tesseract_err"% (filename, out_basename, lang, config))

    #os.unsetenv('LD_PRELOAD')
    os.unsetenv('TESSDATA_PREFIX')
    try:
        fd = open(out_basename + ".txt")
        txt = fd.read()
        fd.close()
    except:
        txt = None
    return txt
