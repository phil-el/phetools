# -*- coding: utf-8 -*-
#
# @file serialize.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import sys
import types
import json
import os

# php serializer, support only base type, list, tuple and dict, no support
# for set nor object
def serialize_php_int(var):
    return "i:%d;" % (var)

def serialize_php_string(var):
    return 's:%d:"%s";' % (len(var), var)

def serialize_php_float(var):
    return "d:%s;" % (var)

def serialize_php_error(var):
    raise TypeError("Invalid Type %s" % (type(var)))

def serialize_php_bool(var):
    return "b:%d;" % (var)

def serialize_php_none(var):
    return "N;"

# Special case for none as dict index
def serialize_php_none_as_zero(var):
    return serialize_php_int(0);

def serialize_php_array_key(var):
    serializer = {
        types.IntType : serialize_php_int,
        types.FloatType : serialize_php_int,
        types.BooleanType : serialize_php_int,
        types.StringType : serialize_php_string,
        types.NoneType : serialize_php_none_as_zero,
        }
    return serializer.get(type(var), serialize_php_error)(var);

def serialize_php_array(var):
    values = []
    for index, value in enumerate(var):
        values.append(serialize_php_array_key(index))
        values.append(serialize_php(value))
    return "a:%d:{%s}" % (len(var), "".join(values))

def serialize_php_dict(var):
    values = []
    for index, value in var.iteritems():
        values.append(serialize_php_array_key(index))
        values.append(serialize_php(value))
    return "a:%d:{%s}" % (len(var), "".join(values))

def serialize_php(var):
    serializer = {
        types.IntType : serialize_php_int,
        types.LongType : serialize_php_int,
        types.StringType : serialize_php_string,
        types.BooleanType : serialize_php_bool,
        types.NoneType : serialize_php_none,
        types.ListType : serialize_php_array,
        types.TupleType : serialize_php_array,
        types.DictType : serialize_php_dict,
        }
    return serializer.get(type(var), serialize_php_error)(var);

class SerializerBase:
    def __init__(self, serializer_type):
        self.serializer_type = serializer_type
        self.is_text = serializer_type.endswith('fm')

    def content_type(self):
        return 'text/plain' if self.is_text else self.mime_type()

    def mime_type(self):
        return 'text/plain'

    def serialize(self, result):
        text = ''
        for r in result:
            text += str(r) + ': ' + str(result[r]) + '\n'
        return text

class SerializerJson(SerializerBase):
    def __init__(self, serializer_type):
        SerializerBase.__init__(self, serializer_type)

    def mime_type(self):
        return 'application/json'

    def serialize(self, result):
        return json.dumps(result)

class SerializerPhp(SerializerBase):
    def __init__(self, serializer_type):
        SerializerBase.__init__(self, serializer_type)

    def mime_type(self):
        return 'application/php'

    def serialize(self, result):
        return serialize_php(result)

def get_serializer(serializer_type, user_serializer = None):
    real_type = serializer_type
    if serializer_type.endswith("fm"):
        real_type = serializer_type[:-2]
    serializer = {
        'dump' : SerializerBase,
        'json' : SerializerJson,
        'php'  : SerializerPhp,
        }
    if not user_serializer:
        user_serializer = {}
    serializer.update(user_serializer)

    return serializer.get(real_type, SerializerBase)(serializer_type)

if __name__ == "__main__":
    serializer = get_serializer("json")
    print serializer.content_type()
    print serializer.serialize({ "a" : 1, "b": [ 1, 2, 3] })
