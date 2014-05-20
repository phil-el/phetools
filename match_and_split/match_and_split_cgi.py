#!/usr/bin/python
# -*- coding: utf-8 -*-
# GPL V2, author phe

# FIXME: *_cgi.py are nearly identical, share the code

import sys
sys.path.append('/data/project/phetools/phe/common')
import simple_redis_ipc
import json

def handle_query(params):
    return simple_redis_ipc.send_command('match_and_split_daemon', params, 240)

def query_params(environ):
    import cgi
    field = cgi.FieldStorage(environ['wsgi.input'])
    rdict = {
        'cmd'   : 'status',
        'title' : '',
        'user'  : '',
        'lang'  : ''
        }
    for name in field:
        rdict[name] = field[name].value

    return rdict

def myapp(environ, start_response):
    params = query_params(environ)
    if params['cmd'] == 'status':
        content_type = 'text/html'
    else:
        content_type = 'application/json'

    nr_subscribed, text = handle_query(params)

    # FIXME: revisit encoding, all text must be unicode and must be encoded
    # as utf-8.
    if not nr_subscribed:
        text = 'match and split robot is not running.\n Please try again later.'
        if params['cmd'] != 'status':
            text = json.dumps({ 'error' : 3, 'text' : text})
    elif params['cmd'] != 'status':
        text = json.dumps(text)
    elif text:
        text = text.encode('utf-8')
    else:
        # FIXME: likely to be a timeout from the server side, a better
        # msg here is needed
        text = ''

    start_response('200 OK',
                   [('Content-Type', content_type),
                    ('Content-Length', len(text)),
                    ('Access-Control-Allow-Origin', '*')
                    ])

    return [ text ]


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import traceback
        from flup.server.cgi import WSGIServer
        try:
            WSGIServer(myapp).run()
        except BaseException as e:
            print >> sys.stderr, str(e)
            print >> sys.stderr, traceback.format_exc()
            raise
    else:
        try:
            import urllib
            request = {
                'cmd' : 'status',
                'user' : 'Phe',
                'lang' : 'fr',
                'title' : urllib.quote(sys.argv[1])
                }

            print >> sys.stderr, handle_query(request)
        except KeyboardInterrupt:
            import os
            os._exit(1)
