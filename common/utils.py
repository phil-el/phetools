#!/usr/bin/python3

import pickle
from pathlib import Path
import hashlib
import bz2
import gzip
import os
import errno
import urllib.request, urllib.parse
import sys
import time


def read_file(filename):
    text = Path(filename).read_text(encoding='utf-8')
    return text


def write_file(filename, text):
    Path(filename).write_text(text, encoding='utf-8')


# a simple serializer
def save_obj(filename, data):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)


def load_obj(filename):
    with open(filename, 'rb') as f:
        data = pickle.load(f)
    return data


def sha1(filename):
    with open(filename, 'rb') as f:
        h = hashlib.sha1()
        data = True
        while data:
            data = f.read(4096)
            if data:
                h.update(data)
    sha1 = h.hexdigest()
    return sha1


def write_sha1(sha1, filename):
    with open(filename, 'w') as f:
        f.write(sha1)


def url_opener():
    opener = urllib.request.URLopener()
    opener.addheaders = [('User-agent', 'MW_phetools')]
    return opener


def copy_file_from_url(url, out_file, expect_sha1=None, max_retry=4):
    retry = 0
    max_retry = min(max(1, max_retry), 5)
    ok = False
    url = urllib.parse.quote(url, safe=':/%')
    while not ok and retry < max_retry:
        try:
            opener = url_opener()
            fd_in = opener.open(url)
            fd_out = open(out_file, "wb")
            data = True
            while data:
                data = fd_in.read(4096)
                if data:
                    fd_out.write(data)
            fd_in.close()
            fd_out.close()
            if expect_sha1:
                if sha1(out_file) != expect_sha1:
                    retry += 1
                    if retry < max_retry:
                        time.sleep(60 * (retry << 1))
                else:
                    ok = True
            else:
                ok = True
        except OSError as e:
            if e[0] == 'http error' and e[1] == 302:
                new_url = e[3]['Location']  # todo: getting by index is deprecated and will raise error
                return copy_file_from_url(new_url, out_file, expect_sha1, max_retry - 1)
            raise
        except Exception:
            print_traceback("upload error:", url, out_file)
            if os.path.exists(out_file):
                os.remove(out_file)
            retry += 1
            if retry < max_retry:
                time.sleep(60 * (retry << 1))

    if retry:
        if ok:
            print(f"upload success after {retry} retry", url, out_file, file=sys.stderr)
        else:
            print(f"upload failure after {retry} retry", url, out_file, url, out_file, file=sys.stderr)

    return ok


def compress_file_data(out_filename, data, compress_type):
    if compress_type in ['bzip2', 'gzip']:
        if compress_type == 'bzip2':
            f_out = bz2.BZ2File(out_filename + '.bz2', 'wb')
        else:
            f_out = gzip.open(out_filename + '.gz', 'wb')
        f_out.write(data)
        f_out.close()
    else:
        raise ValueError('Unhandled compression scheme: ' + compress_type)


def compress_file(out_filename, in_filename, compress_type):
    with open(in_filename, 'rb') as f:
        compress_file_data(out_filename, f.read(), compress_type)


# return None if the file doesn't exist, raise a ValueError if compress_type
# is not supported or compress_type == []. Note than returning '' and None
# are different, '' means the file exists and is empty, None means the file
# doesn't exists.
def uncompress_file(filename, compress_types):
    if isinstance(compress_types, str):
        compress_types = [compress_types]

    for ctype in compress_types:
        f = None
        if ctype == 'bzip2':
            if os.path.exists(filename + '.bz2'):
                f = bz2.BZ2File(filename + '.bz2')
        elif ctype == 'gzip':
            if os.path.exists(filename + '.gz'):
                f = gzip.open(filename + '.gz')
        elif ctype == '' or ctype is None:
            if os.path.exists(filename):
                f = open(filename)
        else:
            raise ValueError('Unhandled compression scheme: ' + ctype)
        if f:
            data = f.read()
            f.close()
            return data


# Protect a call against EINTR.
def _retry_on_eintr(func, *args):
    while True:
        try:
            return func(*args)
        except OSError as e:
            # print("EINTR, retrying")
            if e.errno != errno.EINTR:
                raise
            continue


def safe_read(fd):
    return _retry_on_eintr(fd.read)


def safe_write(fd, text):
    return _retry_on_eintr(fd.write, text)


def print_traceback(*kwargs):
    import traceback
    try:
        traceback.print_exc()
        if len(kwargs):
            print("arguments:", file=sys.stderr)
            for f in kwargs:
                print(f, file=sys.stderr)
            print('', file=sys.stderr)
    except:
        print("ERROR: An exception occured during traceback", file=sys.stderr)
        raise


# File can be written during reading but it's assumed write are line buffered
# or caller must ignore the first line because it can be a partial line.
def readline_backward(filename, buf_size=8192):
    with open(filename) as fh:
        offset = 0
        partial_line = None
        fh.seek(0, os.SEEK_END)
        total_size = left_size = fh.tell()
        # Ensure we do aligned read on buf_size.
        block_size = total_size % buf_size
        first = True
        while left_size:
            offset = min(total_size, offset + block_size)
            fh.seek(total_size - offset, os.SEEK_SET)
            buf = fh.read(min(left_size, block_size))
            left_size = max(0, left_size - block_size)
            lines = buf.split('\n')
            if first:
                # The first block can end with a \n, remove it else
                # we will get an empty line at start of output.
                if not lines[-1]:
                    lines = lines[:-1]
                # After the first block read the full buffer size.
                block_size = buf_size
            first = False
            if partial_line:
                lines[-1] += partial_line
            partial_line = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                yield lines[index]
        yield partial_line
