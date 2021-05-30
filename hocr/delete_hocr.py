# -*- coding: utf-8 -*-
#
# @file delete_hocr.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import os
import hocr_request
import hocr
from common import db


def delete(bookname, lang):
    if type(bookname) == type(u''):
        bookname = bookname.encode('utf-8')
    bookname = bookname.replace(' ', '_')
    path = hocr.cache_path(bookname, lang)
    sha1 = hocr.read_sha1(path)

    db_hocr = hocr_request.DbHocr()
    with db.connection(db_hocr):
        q = 'delete from hocr where sha1=%s and lang=%s and title=%s'
        db_hocr.cursor.execute(q, [sha1, lang, bookname])
        print db_hocr.cursor.fetchall()
    if os.path.exists(path + 'sha1.sum'):
        os.remove(path + 'sha1.sum')


if __name__ == "__main__":
    db_hocr = hocr_request.DbHocr()
    db_hocr.open()
    q = 'select title, lang from hocr where lang="bn"'
    db_hocr.cursor.execute(q)
    for p in db_hocr.cursor.fetchall():
        print p['lang'], p['title']
        # commented for safety
        # delete(p['title'], p['lang'])

    db_hocr.close()
