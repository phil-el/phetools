#!/usr/bin/python
# -*- coding: utf-8 -*-

import cPickle
import hashlib
import bz2
import gzip
import os
import errno
import urllib
import sys
import time

def read_file(filename):
    fd = open(filename)
    text =  unicode(fd.read(), 'utf-8')
    fd.close()
    return text

def write_file(filename, text):
    fd = open(filename, 'w')
    fd.write(text.encode('utf-8'))
    fd.close()

# a simple serializer
def save_obj(filename, data):
    fd = open(filename, 'wb')
    cPickle.dump(data, fd)
    fd.close()

def load_obj(filename):
    fd = open(filename, 'rb')
    data = cPickle.load(fd)
    fd.close()
    return data

def sha1(filename):
    fd = open(filename)
    h = hashlib.sha1()
    data = True
    while data:
        data = fd.read(4096)
        if data:
            h.update(data)
    fd.close()

    return h.hexdigest()

def write_sha1(sha1, filename):
    fd = open(filename, 'w')
    fd.write(sha1)
    fd.close()

def url_opener():
    opener = urllib.URLopener()
    opener.addheaders = [('User-agent', 'MW_phetools')]
    return opener

def copy_file_from_url(url, out_file, expect_sha1 = None, max_retry = 4):
    retry = 0
    max_retry = min(max(1, max_retry), 5)
    ok = False
    url = urllib.quote(url, safe=':/%')
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
                        time.sleep(60*(retry << 1))
                else:
                    ok = True
            else:
                ok = True
        except Exception:
            print_traceback("upload error:", url, out_file)
            if os.path.exists(out_file):
                os.remove(out_file)
            retry += 1
            if retry < max_retry:
                time.sleep(60*(retry << 1))

    if retry:
        if ok:
            print >> sys.stderr, "upload success after %d retry" % retry, url, out_file
        else:
            print >> sys.stderr, "upload failure after %d retry" % retry, url, out_file

    return ok

def compress_file_data(out_filename, data, compress_type):
    if compress_type in ['bzip2', 'gzip']:
        if compress_type == 'bzip2':
            f_out = bz2.BZ2File(out_filename + '.bz2', 'wb')
        elif compress_type == 'gzip':
            f_out = gzip.open(out_filename + '.gz', 'wb')
        f_out.write(data)
        f_out.close()
    else:
        raise ValueError('Unhandled compression scheme: ' + str(compress_type))

def compress_file(out_filename, in_filename, compress_type):
    f_in = open(in_filename)
    compress_file_data(out_filename, f_in.read(), compress_type)
    f_in.close()

# return None if the file doesn't exist, raise a ValueError if compress_type
# is not supported or compress_type == []. Note than returning '' and None
# are different, '' means the file exists and is empty, None means the file
# doesn't exists.
def uncompress_file(filename, compress_type):
    if type(compress_type) == type([]):
        for compress in compress_type:
            data = uncompress_file(filename, compress)
            if data != None:
                return data
        return None
    else:
        fd_in = None
        if compress_type == 'bzip2':
            if os.path.exists(filename + '.bz2'):
                fd_in = bz2.BZ2File(filename + '.bz2')
        elif compress_type == 'gzip':
            if os.path.exists(filename + '.gz'):
                fd_in = gzip.open(filename + '.gz')
        elif compress_type == '':
            if os.path.exists(filename):
                fd_in = open(filename)
        else:
            raise ValueError('Unhandled compression scheme: ' + str(compress_type))

        if fd_in == None:
            return None
        data = fd_in.read()
        fd_in.close()
        return data

    raise ValueError('Empty compression scheme: ' + str(compress_type))

# Protect a call against EINTR.
def _retry_on_eintr(func, *args):
    while True:
        try:
            return func(*args)
        except (IOError, OSError) as e:
            #print "EINTR, retrying"
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
            print >> sys.stderr, "arguments:",
            for f in kwargs:
                if type(f) == type(u''):
                    f = f.encode('utf-8')
                print >> sys.stderr, str(f),
            print >> sys.stderr
    except:
        print >> sys.stderr, "ERROR: An exception occured during traceback"
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
