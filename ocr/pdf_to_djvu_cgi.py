# -*- coding: utf-8 -*-
#
# @file pdf_to_djvu_cgi.py
#
# @remark Copyright 2016 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import json
import pdf_to_djvu
import sys
import os
sys.path.append(os.path.expanduser('~/phe/common'))
sys.path.append(os.path.expanduser('~/phe/jobs'))
import sge_jobs
import utils

def queue_pdf_to_djvu(ia_id):
    job_req = {
        'jobname' : 'pdf_to_djvu',
        'run_cmd' : 'python',
        'force' : True,
        'args' : [
            os.path.expanduser('~/phe/ocr/pdf_to_djvu.py'),
            # FIXME: later use command line switch to provide a more general
            # service
            ia_id,
            ],
        'max_vmem' : 2048,
        }

    db_obj = sge_jobs.DbJob()

    print job_req

    db_obj.add_request(**job_req)

def query_params(environ):
    import cgi
    field = cgi.FieldStorage(fp = environ['wsgi.input'], environ = environ)
    rdict = {
        'format' : 'text',
        'cmd' : 'status',
        'ia_id' : '',
    }
    for name in field:
        rdict[name] = field[name].value

    return rdict

def handle_query(params, start_response):
    print >> sys.stderr, params

    answer = '200 OK'

    if not params['ia_id']:
        answer = '400 BAD REQUEST'
        text = json.dumps({
            'error' : 1,
            'text' : 'No ia identifier provided in request',
        })
    else:
        # Check it now to provide directly feedback to user
        ia_files = pdf_to_djvu.get_ia_files(params['ia_id'])
        if not ia_files.get('pdf', None) or not ia_files.get('xml', None):
            answer = '400 BAD REQUEST'
            text = json.dumps(
                { 'error' : 2,
                  'text' : "invalid ia identifier, I can't locate needed files",
              })

    if answer == '200 OK':
        queue_pdf_to_djvu(params['ia_id'])
        text = json.dumps({
            'error' : 0,
            'text' : 'item conversion will start soon',
        })

    start_response(answer, [('Content-Type', 'text/plain; charset=UTF-8'),
                            ('Content-Length', str(len(text))),
                            ('Access-Control-Allow-Origin', '*')])
    return [ text ]

# FIXME: this piece of code is too clumsy
def handle_get(environ, params, start_response):
    if not params['ia_id']:
        text = json.dumps({
            'error' : 1,
            'text' : 'No ia identifier provided in request',
        })
        start_response("400 BAD REQUEST",
                       [('Content-Type', 'text/plain; charset=UTF-8'),
                        ('Content-Length', str(len(text))),
                        ('Access-Control-Allow-Origin', '*')])
        return [ text ]

    ia_files = pdf_to_djvu.get_ia_files(params['ia_id'])
    if not ia_files.get('pdf', None) or not ia_files.get('xml', None):
        text = json.dumps(
            { 'error' : 2,
              'text' : "invalid ia identifier, I can't locate needed files",
          })
        start_response("400 BAD REQUEST",
                       [('Content-Type', 'text/plain; charset=UTF-8'),
                        ('Content-Length', str(len(text))),
                        ('Access-Control-Allow-Origin', '*')])
        return [ text ]

    djvu_name = os.path.expanduser('~/cache/ia_pdf/')
    djvu_name += ia_files['pdf']['name'][:-3] + 'djvu'
    if not os.path.exists(djvu_name):
        text = json.dumps(
            { 'error' : 3,
              'text' : "Can't locate djvu file, ia id is valid, perhaps conversion failed or is in progress",
          })
        start_response("400 BAD REQUEST",
                       [('Content-Type', 'text/plain; charset=UTF-8'),
                        ('Content-Length', str(len(text))),
                        ('Access-Control-Allow-Origin', '*')])
        return [ text ]

    if 'wsgi.file_wrapper' in environ:
        return environ['wsgi.file_wrapper'](the_file , 1024)
    else:
        fd = open(djvu_name)
        start_response("200 OK",
                       [('Content-Type', 'application/octet-stream'),
                        ('Access-Control-Allow-Origin', '*')])

        def file_wrapper(fileobj, block_size=1024):
            try:
                data = fileobj.read(block_size)
                while data:
                    yield data
                    data = fileobj.read(block_size)
            finally:
                fileobj.close()

        return file_wrapper(fd, 1024)

def handle_status(start_response):
    # pseudo ping, as we run on the web server, we always return 1 ms.
    text = json.dumps( { 'error' : 0,
                         'text' : 'pong',
                         'server' : 'pdf_to_djvu_cgi',
                         'ping' : 0.001
                        } )

    start_response('200 OK', [('Content-Type',
                               'text/plain; charset=UTF-8'),
                              ('Content-Length', str(len(text))),
                              ('Access-Control-Allow-Origin', '*')])
    return [ text ]

def myapp(environ, start_response):
    params = query_params(environ)

    if params['cmd'] == 'ping':
        return handle_ping(start_response)
    elif params['cmd'] == 'convert':
        return handle_query(params, start_response)
    elif params['cmd'] == 'get':
        return handle_get(environ, params, start_response)
    else:
        return handle_status(start_response)

if __name__ == "__main__":
    sys.stderr = open(os.path.expanduser('~/log/pdf_to_djvu_cgi.err'), 'a')

    from flup.server.cgi import WSGIServer
    try:
        WSGIServer(myapp).run()
    except BaseException:
        utils.print_traceback()
