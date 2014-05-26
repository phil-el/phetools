# -*- coding: utf-8 -*-

import sys
import types

from get_credit import get_credit

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

# FIXME: in it's own module
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

class formater_base:
    def __init__(self, format):
        self.format_type = format
        self.raw = format.endswith('fm')

    def is_raw(self):
        return self.raw

    def content_type(self):
        if self.is_raw():
            return 'text/plain'
        return self.mime_type()

    def mime_type(self):
        return 'text/plain'

    def format(self, result):
        text = ''
        for r in result:
            text += str(r) + ': ' + str(result[r]) + '\n'
        return text

class formater_html(formater_base):
    def __init__(self, format):
        formater_base.__init__(self, format)

    def mime_type(self):
        return 'text/html'

    def format(self, result):
        html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head></head>
<body>"""
        for r in result:
            html += str(r) + ': ' + str(result[r]) + '<br />'
        return html + "</body></html>"

class formater_json(formater_base):
    def __init__(self, format):
        formater_base.__init__(self, format)

    def mime_type(self):
        return 'application/json'

    def format(self, result):
        import json
        return json.dumps(result)

class formater_php(formater_base):
    def __init__(self, format):
        formater_base.__init__(self, format)

    def mime_type(self):
        return 'application/php'

    def format(self, result):
        return serialize_php(result)

def get_formater(format):
    real_format = format
    if format.endswith("fm"):
        real_format = format[:-2]
    formater = {
        'text' : formater_base,
        'html' : formater_html,
        'json' : formater_json,
        'php'  : formater_php,
        }
    return formater.get(real_format, formater_base)(format)

def split_param(params):
    if params:
        return params.split('|')
    return []

def query_params(environ):
    import cgi
    field = cgi.FieldStorage(environ['wsgi.input'])
    rdict = { 'format' : 'text',
              'book' : '',
              'page' : '',
              'image' : '',
              'lang' : '' }
    for name in field:
        rdict[name] = field[name].value
    rdict['book'] = split_param(rdict['book'])
    rdict['page'] = split_param(rdict['page'])
    rdict['image'] = split_param(rdict['image'])

    print >> sys.stderr, str(rdict)

    return rdict

def handle_query(params, start_response):
    # FIXME: handle ill formed request (400)
    result = get_credit(domain = params['lang'],
                        family = 'wikisource',
                        books = params['book'],
                        pages = params['page'],
                        images = params['image'])

    formater = get_formater(params['format'])
    text = formater.format(result)
    start_response('200 OK', [('Content-Type',
                               formater.content_type() + '; charset=UTF-8'),
                              ('Content-Length', len(text)),
                              ('Access-Control-Allow-Origin', '*')])
    return [ text ]

def handle_status(start_response):
    text = "I'm up"
    start_response('200 OK', [('Content-Type',
                               'text/plain; charset=UTF-8'),
                              ('Content-Length', len(text)),
                              ('Access-Control-Allow-Origin', '*')])
    return [ text ]

def myapp(environ, start_response):
    params = query_params(environ)

    # Note than &status or &status= doesn't works cgi.FieldStorage expect
    # &status=something to accept to store a parameter, so ?lang=fr&status=
    # will return 200 and an empty answer, counter-intuitive...
    if params['lang'] and not params.has_key('status'):
        return handle_query(params, start_response)
    else:
        return handle_status(start_response)

if __name__ == "__main__":
    import traceback
    from flup.server.cgi import WSGIServer
    try:
        WSGIServer(myapp).run()
    except BaseException as e:
        print >> sys.stderr, str(e)
        print >> sys.stderr, traceback.format_exc()
        raise
