#!/usr/bin/python
# -*- coding: utf-8 -*-

import cPickle

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
