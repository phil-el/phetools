#
# @file hocr.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import sys
import os
from common import utils
import hashlib
from ocr import pdf_to_djvu
from ocr import ocr_djvu
from ocr import djvu_text_to_hocr
from ocr import ocr
from common import db
import re


def lang_to_site(lang):
    sites = {
        'nb': 'no',
    }

    return sites.get(lang, lang)


tmp_dir = os.path.expanduser('~/tmp/hocr/')


def get_tmp_dir(lang):
    return tmp_dir + lang + '/'


def bookname_md5(book_name):
    h = hashlib.md5()
    h.update(book_name.encode())
    return h.hexdigest()


def cache_path(book_name, lang):
    base_dir = os.path.expanduser('~/cache/hocr/') + '%s/%s/%s/'
    h = bookname_md5(book_name + lang_to_site(lang))
    return base_dir % (h[0:2], h[2:4], h[4:])


def read_sha1(path):
    with open(path + 'sha1.sum') as f:
        sha1 = f.read()
    return sha1


def check_sha1(path, sha1):
    if os.path.exists(path + 'sha1.sum'):
        old_sha1 = read_sha1(path)
        if old_sha1 == sha1:
            return True
    return False


def check_and_upload(url, filename, sha1):
    if not os.path.exists(filename) or utils.sha1(filename) != sha1:
        if not utils.copy_file_from_url(url, filename, sha1):
            return False
    return True


def db_sha1(domain, family, bookname):
    conn = db.create_conn(domain=domain, family=family)
    cursor = db.use_db(conn, domain, family)

    q = 'SELECT img_sha1 FROM image WHERE img_name = %s'
    cursor.execute(q, [bookname])
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data[0][0] if len(data) else None


def get_sha1(lang, bookname):
    url = None
    md5 = bookname_md5(bookname)
    commons = False

    sha1 = db_sha1(lang, 'wikisource', bookname)
    if not sha1:
        sha1 = db_sha1('commons', 'wiki', bookname)
        commons = True

    if sha1:
        sha1 = "%040x" % int(sha1, 36)
        # FIXME: don't hardcode this.
        url = 'https://upload.wikimedia.org/wikisource/%s/' % lang
        if commons:
            url = 'https://upload.wikimedia.org/wikipedia/commons/'
        url += md5[0] + '/' + md5[0:2] + '/' + bookname

    return sha1, url


# check if data are uptodate
#
# return:
# -1 if the File: doesn't exist
# -2 and exception occured during file copy
#  0 data exist and uptodate
#  1 File: exists but data outdated or not existing
# if it return 1 the file is uploaded if it didn't already exists.
def is_uptodate(lang, book):
    path = cache_path(book, lang)

    url = None

    sha1, url = get_sha1(lang, book)
    if not sha1:
        return -1

    if check_sha1(path, sha1):
        return 0

    if not os.path.exists(path):
        os.makedirs(path)

    # This is racy, if two hocr try to create the same directory, the directory
    # can't exist when testing it but is created by the other process before
    # makedirs() is called, so protect it with a try/except.
    temp_dir = get_tmp_dir(lang)
    if not os.path.exists(temp_dir):
        try:
            os.makedirs(temp_dir)
        except OSError as e:
            import errno
            if e.errno != errno.EEXIST:
                raise

    if not check_and_upload(url, temp_dir + book, sha1):
        return -2

    return 1


def write_sha1(out_dir, in_file):
    sha1 = utils.sha1(in_file)
    utils.write_sha1(sha1, out_dir + "sha1.sum")


def fast_hocr(book, lang):
    print("fast_hocr")
    path = cache_path(book, lang)
    print("out_dir:", path)
    options = djvu_text_to_hocr.default_options()
    options.compress = 'bzip2'
    options.out_dir = path
    options.silent = True

    in_file = get_tmp_dir(lang) + book

    if djvu_text_to_hocr.parse(options, in_file) == 0:
        return True

    return False


def slow_hocr(lang, book, in_file):
    print("slow_hocr")
    path = cache_path(book, lang)
    print("out_dir:", path)

    options = ocr_djvu.default_options()

    options.silent = True
    options.compress = 'bzip2'
    options.config = 'hocr'
    options.num_thread = 1
    options.lang = ocr.tesseract_languages.get(lang, 'eng')
    options.out_dir = path

    print("Using tesseract lang:", options.lang)

    ret = ocr_djvu.ocr_djvu(options, in_file)

    # FIXME: should go in ocr_djvu.cleanup() but better if cleanup() can
    # be triggered by some sort of ocr_djvu module unload
    try:
        os.rmdir(options.temp_tiff_dir)
    except:
        print("unable to remove directory:", options.temp_tiff_dir, file=sys.stderr)

    return ret


# is_uptodate() must be called first to ensure the file is uploaded.
def hocr(options):
    path = cache_path(options.book, options.lang)
    if os.path.exists(path + 'sha1.sum'):
        os.remove(path + 'sha1.sum')

    in_file = get_tmp_dir(options.lang) + options.book
    done = False
    if in_file.endswith('.pdf'):
        # Don't do slow hocr for ws.ru as .pdf ==> slow_hocr, don't try to
        # convert pdf to djvu for ru.ws
        if options.lang != 'ru':
            djvuname = pdf_to_djvu.pdf_to_djvu(in_file)
        else:
            djvuname = None
    else:
        djvuname = in_file
        if options.lang != 'bn' and djvu_text_to_hocr.has_word_bbox(in_file):
            done = fast_hocr(options.book, options.lang)

    # djvuname == None if pdf_to_djvu() fail to convert the file
    if not done and djvuname and options.lang != 'ru':
        done = slow_hocr(options.lang, options.book, djvuname)

    # never fail for ws.ru, see above.
    if done or options.lang == 'ru':
        write_sha1(path, in_file)

    if djvuname:
        os.remove(djvuname)

    if djvuname != in_file:
        os.remove(in_file)

    return done


def update_db(lang, bookname):
    import hocr_request

    db_hocr = hocr_request.DbHocr()
    with db.connection(db_hocr):
        path = cache_path(bookname, lang)
        if os.path.exists(path + 'sha1.sum'):
            sha1 = read_sha1(path)
            db_hocr.add_update_row(bookname, lang, sha1)
        else:
            print("Can't locate sha1.sum", path, file=sys.stderr)


def ret_val(error, text):
    if error:
        print(f"Error: {error}, {text}", file=sys.stderr)
    return {'error': error, 'text': text}


def get_hocr(lang, title):
    # FIXME, delete all no ocr and redo them with nb code lang.
    if lang == 'nb':
        lang = 'no'

    title = title.replace(' ', '_')

    try:
        if lang == 'bn':
            page_nr = re.sub(r'^.*/([০-৯]+)$', r'\1', title)
            book_name = re.sub(r'^(.*?)(/[০-৯]+)?$', r'\1', title)
            result = ord(page_nr[0]) - ord('০')
            for ch in page_nr[1:]:
                result *= 10
                result += ord(ch) - ord('০')
            page_nr = result
        else:
            page_nr = re.sub(r'^.*/([0-9]+)$', r'\1', title)
            book_name = re.sub(r'^(.*?)(/[0-9]+)?$', r'\1', title)
            page_nr = int(page_nr)
    except:
        return ret_val(1, "unable to extract page number from page: " + title)

    path = cache_path(book_name, lang)

    filename = f'{path}page_{page_nr:04}.hocr'

    # We support data built with different compress scheme than the one
    # actually generated by the server
    text = utils.uncompress_file(filename, ['bzip2', 'gzip', ''])
    if text is None:
        # not available, add a request to do this hocr so we build data
        # lazilly but we filter here unsupported file type
        if book_name.endswith('.djvu') or book_name.endswith('.pdf'):
            import hocr_request
            hocr_request.add_hocr_request(lang, book_name, True)
        return ret_val(1, "unable to locate file %s for page %s lang %s" % (filename, book_name, lang))

    # work-around https://code.google.com/p/tesseract-ocr/issues/detail?id=690&can=1&q=utf-8
    # a simple patch exists: https://code.google.com/p/tesseract-ocr/source/detail?r=736#
    # but it's easier to do a double conversion to remove invalid utf8
    # rather than to maintain a patched version of tesseract.
    # text = text.decode('utf-8', 'ignore')
    # text = text.encode('utf-8', 'ignore')
    # todo: Is it still need in Python 3? The urls was deleted long ago.
    text = text.encode("utf-8", "replace").decode("utf-8", "replace")

    return ret_val(0, text)


def default_options():
    class Options:
        pass

    options = Options()
    options.book = None
    options.lang = None

    return options


def main():
    options = default_options()

    for arg in sys.argv[1:]:
        if arg == '-help':
            pass
        elif arg.startswith('-book:'):
            options.book = arg[len('-book:'):]
            options.book = options.book.replace(' ', '_')
        elif arg.startswith('-lang:'):
            options.lang = arg[len('-lang:'):]
        else:
            print('unknown option:', sys.argv, file=sys.stderr)
            exit(1)

    if not options.book or not options.lang:
        print('missing option -lang: and/or -book:', sys.argv, file=sys.stderr)
        exit(1)

    ret = is_uptodate(options.lang, options.book)
    if ret > 0:
        if not hocr(options):
            print('Error, hocr fail', file=sys.stderr)
            ret = 2
        else:
            update_db(options.lang, options.book)
            ret = 0
    elif ret < 0:
        print("Error, file doesn't exist:", ret, file=sys.stderr)
        ret = 3 + abs(ret)
    else:
        update_db(options.lang, options.book)

    return ret


if __name__ == '__main__':
    cache_dir = 'hocr'
    if not os.path.exists(os.path.expanduser('~/cache/' + cache_dir)):
        os.mkdir(os.path.expanduser('~/cache/' + cache_dir))
    try:
        ret = main()
    except:
        utils.print_traceback()
        exit(4)

    exit(ret)
