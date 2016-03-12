# -*- coding: utf-8 -*-

import sys
import json
import os
sys.path.append(os.path.expanduser('~/phe/common'))
import serialize
import random
from get_credit import get_credit

class SerializerHtml(serialize.SerializerBase):
    def __init__(self, serializer_type):
        serialize.SerializerBase.__init__(self, serializer_type)

    def mime_type(self):
        return 'text/html'

    def serialize(self, result):
        html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head></head>
<body>"""
        for r in result:
            html += str(r) + ': ' + str(result[r]) + '<br />'
        return html + "</body></html>"

def get_serializer(serializer_type):
    html_serializer = { 'html' : SerializerHtml }
    return serialize.get_serializer(serializer_type, html_serializer)

def split_param(params):
    if params:
        return params.split('|')
    return []

def query_params(environ):
    import cgi
    field = cgi.FieldStorage(fp = environ['wsgi.input'], environ = environ)
    rdict = { 'format' : 'text',
              'cmd' : 'history',
              'book' : '',
              'page' : '',
              'image' : '',
              'lang' : '' }
    for name in field:
        rdict[name] = field[name].value
    rdict['book'] = split_param(rdict['book'])
    rdict['page'] = split_param(rdict['page'])
    rdict['image'] = split_param(rdict['image'])

    if rdict['lang'] in [ 'www', '' ]:
        rdict['lang'] = 'old'

    return rdict

def handle_query(params, start_response):
    # Avoid to flood log.
    if not random.randint(0, 100) % 100:
        print >> sys.stderr, params

    # FIXME: handle ill formed request (400)
    result = get_credit(domain = params['lang'],
                        family = 'wikisource',
                        books = params['book'],
                        pages = params['page'],
                        images = params['image'])

    serializer = get_serializer(params['format'])
    text = serializer.serialize(result)
    start_response('200 OK', [('Content-Type',
                               serializer.content_type() + '; charset=UTF-8'),
                              ('Content-Length', str(len(text))),
                              ('Access-Control-Allow-Origin', '*')])
    return [ text ]

def handle_status(start_response):
    # pseudo ping, as we run on the web server, we always return 1 ms.
    text = json.dumps( { 'error' : 0,
                         'text' : 'pong',
                         'server' : 'history_credit', 
                         'ping' : 0.001
                        } )

    start_response('200 OK', [('Content-Type',
                               'text/plain; charset=UTF-8'),
                              ('Content-Length', str(len(text))),
                              ('Access-Control-Allow-Origin', '*')])
    return [ text ]

def myapp(environ, start_response):
    params = query_params(environ)

    # Note than &status or &status= doesn't works cgi.FieldStorage expect
    # &status=something to accept to store a parameter, so ?lang=fr&status=
    # will return 200 and an empty answer, counter-intuitive...
    if params['lang'] and params['cmd'] == 'history':
        return handle_query(params, start_response)
    else:
        return handle_status(start_response)

if __name__ == "__main__":
    sys.stderr = open(os.path.expanduser('~/log/credits.err'), 'a')

    from flup.server.cgi import WSGIServer
    try:
        WSGIServer(myapp).run()
    except BaseException:
        import traceback
        traceback.print_exc()
