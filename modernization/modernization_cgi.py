# -*- coding: utf-8 -*-
#
# @file modernization_cgy.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import os
import sys
import modernization
from common import common_html
from common import utils
import types
import json

def query_params(environ):
    import cgi
    field = cgi.FieldStorage(fp = environ['wsgi.input'], environ = environ)
    rdict = {
        'format' : 'html',
        'cmd' : 'status',
        'title' : '',
        'lang' : ''
        }
    for name in field:
        if type(field[name]) == types.ListType:
            rdict[name] = field[name][-1].value
        else:
            rdict[name] = field[name].value

    for key in rdict:
        rdict[key] = unicode(rdict[key], 'utf-8')

    return rdict

def return_response(start_response, obj, to_json, ret_code, mime_type):
    if to_json:
        try:
            text = json.dumps(obj)
        except UnicodeDecodeError:
            print >> sys.stderr, obj
            ret_code = '400 Bad Request'
            text = json.dumps({ 'error' : 1, 'text' : ret_code })
    else:
        text = obj

    start_response(ret_code, [('Content-Type',
                               mime_type + '; charset=UTF-8'),
                              ('Content-Length', str(len(text))),
                              ('Access-Control-Allow-Origin', '*')])
    return [ text ]


def handle_ping(start_response):

    data = { 'error' : 0,
             'text' : 'pong',
             'server' : 'modernization',
             'ping' : 0.001
             }

    return return_response(start_response, data, True, '200 OK', 'text/plain')

def handle_status(params, start_response):

    text = common_html.get_head('modernization', css = 'shared.css').encode('utf-8') + '\n  <body>\n'

    text += '<h1>OK</h1>'

    text += '  </body>\n</html>'

    return return_response(start_response, text, False, '200 OK', 'text/html')

def handle_suggest_query(params, start_response):
    if params['lang'] and params['title']:
        try:
            modernize = modernization.Modernization(params['lang'])
            result = modernize.suggest_dict(params['title'])
            ret_code = '200 OK'
        except:
            utils.print_traceback()
            ret_code = '500 Internal Server Error'
            result = { 'error' : 1, 'text' : ret_code }
    else:
        ret_code = '400 Bad Request'
        result = { 'error' : 1, 'text' : ret_code }

    return return_response(start_response, result, True, ret_code, 'application/json')

def handle_blacklist_query(params, start_response):
    if params['lang'] and params['blacklist']:
        try:
            modernize = modernization.Modernization(params['lang'])
            blacklist = json.loads(params['blacklist'])
            modernize.save_blacklist(blacklist)
            ret_code = '200 OK'
            result = { 'error' : 0, 'text' :'OK' }
        except:
            utils.print_traceback()
            ret_code = '500 Internal Server Error'
            result = { 'error' : 1, 'text' : ret_code }
    else:
        ret_code = '400 Bad Request'
        result = { 'error' : 1, 'text' : ret_code }

    return return_response(start_response, result, True, ret_code, 'application/json')

def myapp(environ, start_response):
    params = query_params(environ)

    print >> sys.stderr, params

    if params['cmd'] == 'ping':
        return handle_ping(start_response)
    elif params['cmd'] == 'suggest':
        return handle_suggest_query(params, start_response)
    elif params['cmd'] == 'blacklist':
        return handle_blacklist_query(params, start_response)
    else:
        return handle_status(params, start_response)

if __name__ == "__main__":
    sys.stderr = open(os.path.expanduser('~/log/modernization.err'), 'a')

    from flup.server.cgi import WSGIServer
    try:
        WSGIServer(myapp).run()
    except BaseException:
        utils.print_traceback()
