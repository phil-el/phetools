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
sys.path.append(os.path.expanduser('~/phe/common'))
import common_html
import db
sys.path.append(os.path.expanduser('~/wikisource'))
import ws_category
import utils
import types
import json

def query_params(environ):
    import cgi
    field = cgi.FieldStorage(environ['wsgi.input'])
    rdict = {
        'format' : 'html',
        'cmd' : 'status',
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
                              ('Content-Length', len(text)),
                              ('Access-Control-Allow-Origin', '*')])
    return [ text ]

def handle_ping(start_response):

    data = { 'error' : 0,
             'text' : 'pong',
             'server' : 'pages without scan',
             'ping' : 0.001
             }

    return return_response(start_response, data, True, '200 OK', 'text/plain')

def handle_status(params, start_response):

    text = common_html.get_head('pages without scan', css = 'shared.css').encode('utf-8') + '\n  <body>\n'

    text += '<h1>OK</h1>'

    text += '  </body>\n</html>'

    return return_response(start_response, text, False, '200 OK', 'text/html')

def page_with_scan(ns, cursor):
    q = '(select distinct page_id from templatelinks left join page on page_id=tl_from where tl_namespace=%s and page_namespace=0)'
    cursor.execute(q, [ ns ])
    return set([ x[0] for x in cursor.fetchall() ])

def disamb_page(cursor):
    q = "select pp_page from page_props where pp_propname = 'disambiguation'"
    cursor.execute(q)
    return set([ x[0] for x in cursor.fetchall() ])

def all_pages(cursor):
    q = 'select page_title, page_len, page_id from page where page_namespace=0 and page_is_redirect=0 ORDER BY page_len'
    cursor.execute(q)
    return cursor.fetchall()


def prev_next_link(prev, size, lang, limit, offset):

    href = False
    if prev:
        label = 'Prev'
        if offset:
            new_offset = max(offset - limit, 0)
            href = True
    else:
        label = 'Next'
        if offset + limit < size:
            new_offset = offset + limit
            href = True

    if href:
        link = '<a href="?cmd=scan&lang=%s' % lang
        if new_offset:
            link += "&offset=%d" % new_offset
        link += "&limit=%d" % limit
        link += '">' + label + '</a>'
    else:
        link = label

    return link

def handle_scan_query(params, start_response):
    text = common_html.get_head('pages without scan', css = 'shared.css').encode('utf-8') + '\n  <body>\n'

    if params['lang']:
        try:
            offset = int(params.get('offset', 0))
            limit = min(500, int(params.get('limit', 500)))
            lang = params['lang']
            conn = db.create_conn(domain = lang, family = 'wikisource')
            cursor = db.use_db(conn, domain = lang, family = 'wikisource')
            ns = ws_category.domain_urls[lang][0]
            page_ids = disamb_page(cursor) | page_with_scan(ns, cursor)
            all_p = all_pages(cursor)
            result = [( unicode(x[0], 'utf-8'), x[1]) for x in all_p if x[2] not in  page_ids]
            text += 'Total: ' + str(len(result)) + '<br />'
            next_link = prev_next_link(False, len(result), lang, limit, offset)
            prev_link = prev_next_link(True, len(result), lang, limit, offset)
            text += prev_link + '&#160;' + next_link + '<br /><br />'

            result = result[offset:offset+limit]
            for x in result:
                text += u'<a href="//%s.wikisource.org/wiki/%s">' % (lang, x[0]) +  x[0].replace('_', ' ') + u'</a>, ' + str(x[1]) + u'<br />'

            text += u'<br />' + prev_link + '&#160;' + next_link
            cursor.close()
            conn.close()
            ret_code = '200 OK'
        except:
            utils.print_traceback()
            ret_code = '500 Internal Server Error'
            text = '<h1>' + ret_code + '</h1>'
    else:
        ret_code = '400 Bad Request'
        text = '<h1>' + ret_code + '</h1>'

    text += '  </body>\n</html>'

    return return_response(start_response, text.encode('utf-8'), False, ret_code, 'text/html')

def myapp(environ, start_response):
    params = query_params(environ)

    print >> sys.stderr, params

    if params['cmd'] == 'ping':
        return handle_ping(start_response)
    elif params['cmd'] == 'scan':
        return handle_scan_query(params, start_response)
    else:
        return handle_status(params, start_response)

if __name__ == "__main__":
    sys.stderr = open(os.path.expanduser('~/log/pages_without_scan.err'), 'a')

    from flup.server.cgi import WSGIServer
    try:
        WSGIServer(myapp).run()
    except BaseException:
        utils.print_traceback()
