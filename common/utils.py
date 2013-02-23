#!/usr/bin/python
# -*- coding: utf-8 -*-

import cPickle
import hashlib

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
