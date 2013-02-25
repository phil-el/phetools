#!/usr/bin/python
# -*- coding: utf-8 -*-

import cPickle
import hashlib
import bz2
import gzip
import os

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
    # FIXME: inefficient in memory usage
    fd = open(filename)
    h = hashlib.sha1()
    h.update(fd.read())
    fd.close()
    h = h.hexdigest()

    return h

def write_sha1(sha1, filename):
    fd = open(filename, 'w')
    fd.write(sha1)
    fd.close()

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
