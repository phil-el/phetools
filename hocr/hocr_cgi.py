#
# @file hocr.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import os
import sys
import json
from jobs import sge_jobs
from common import common_html
import time
import types
from common import utils
import hocr


def log(params):
    try:
        print(params, file=sys.stderr)
    except OSError as e:
        sys.stderr = open(os.path.expanduser('~/log/hocr_cgi.err'), 'a')
        print(params, file=sys.stderr)


def span_anchor(anchor, table):
    return '<span id="' + table + '_' + str(anchor) + '"></span>'


def a_anchor(anchor, table):
    return '<a href="#' + table + '_' + str(anchor) + '">' + str(anchor) + '</a>'


def format_job_table_anchor(anchor):
    return span_anchor(anchor, 'job') + a_anchor(anchor, 'acct')


def format_accounting_table_anchor(anchor):
    return span_anchor(anchor, 'acct') + a_anchor(anchor, 'job')


def format_timestamp(timestamp, fields):
    return time.strftime("%d/%m/%Y %H:%M:%S", time.gmtime(timestamp))


def format_sge_jobnumber_job(sge_jobnumber, fields):
    if not sge_jobnumber:
        return sge_jobnumber
    return format_job_table_anchor(sge_jobnumber)


def format_sge_jobnumber_accounting(sge_jobnumber, fields):
    return format_accounting_table_anchor(sge_jobnumber)


def format_args(args, fields):
    args = json.loads(args)
    if fields['job_run_cmd'] == 'python':
        args = args[1:]
    new_args = []
    prefix = '/data/project/phetools/'
    for a in args:
        if a.startswith(prefix):
            a = '~/' + a[len(prefix):]
        a = a.replace('_', ' ')
        new_args.append(a)
    return ' '.join(new_args)


def format_max_vmem(vmem, fields):
    if not vmem:
        vmem = 0
    return "%.2fM" % (vmem / (1024.0 * 1024))


def format_hostname(hostname, fields):
    suffix = '.eqiad.wmflabs'
    if hostname.endswith(suffix):
        hostname = hostname[:-len(suffix)]
    return hostname


def format_job_id_job(job_id, fields):
    return format_job_table_anchor(job_id)


def format_job_id_accounting(job_id, fields):
    return format_accounting_table_anchor(job_id)


def format_time(t, fields):
    if t:
        return "%.2f" % t
    return str(t)


# fields displayed by cmd=status, [0] is the database field name, [1] is the
# the <th> label, [2] is an optionnal formater function, default formater is
# str(data).
job_table_field = [
    ('job_id', 'job id', format_job_id_job),
    ('job_state', 'job state'),
    ('sge_jobnumber', 'sge job id', format_sge_jobnumber_job),
    ('job_jobname', 'name'),
    ('job_args', 'args', format_args),
    ('job_submit_time', 'submit&nbsp;time&nbsp;(UTC)', format_timestamp),
]

accounting_table_field = [
    ('job_id', 'job id', format_job_id_accounting),
    ('sge_jobnumber', 'sge job id', format_sge_jobnumber_accounting),
    ('sge_hostname', 'host name', format_hostname),
    ('sge_qsub_time', 'submit at', format_timestamp),
    ('sge_start_time', 'start at', format_timestamp),
    ('sge_end_time', 'end at', format_timestamp),
    ('sge_failed', 'failed'),
    ('sge_exit_status', 'exit status'),
    ('sge_ru_utime', 'utime', format_time),
    ('sge_ru_stime', 'stime', format_time),
    ('sge_ru_wallclock', 'wallclock'),
    ('sge_used_maxvmem', 'max vmem', format_max_vmem),
]


def query_params(environ):
    # import cgi
    # field = cgi.FieldStorage(fp = environ['wsgi.input'], environ = environ)
    from urlparse import parse_qsl
    rdict = {
        'format': 'html',
        'cmd': 'status',
        'filter': '',
        'book': '',
        'lang': ''
    }
    for name, value in parse_qsl(environ['QUERY_STRING']):
        rdict[name] = value
    # for name in field:
    #    if type(field[name]) == types.ListType:
    #        rdict[name] = field[name][-1].value
    #    else:
    #        rdict[name] = field[name].value

    return rdict


def handle_ping(start_response):
    # pseudo ping, as we run on the web server, we always return 1 ms.
    text = json.dumps({'error': 0,
                       'text': 'pong',
                       'server': 'hocr',
                       'ping': 0.001
                       })

    start_response('200 OK', [('Content-Type',
                               'text/plain; charset=UTF-8'),
                              ('Content-Length', str(len(text))),
                              ('Access-Control-Allow-Origin', '*')])
    return [text]


def get_int_param(params, name, default, max_val=None):
    try:
        result = params.get(name, default)
        result = int(result)
        if max_val:
            result = min(result, max_val)
    except:
        result = default

    return result


def table_header(fields):
    text = '  <tr>\n'
    for f in fields:
        text += '    <th>' + f[1] + '</th>\n'

    text += '  </tr>\n'

    return text


def to_html(data, fields):
    text = '  <tr>\n'
    for f in fields:
        if f[0] in data:
            text += '    <td>'
            if len(f) >= 3:
                text += str(f[2](data[f[0]], data))
            else:
                text += str(data[f[0]])
            text += '</td>\n'
        else:
            text += '<td>Unknow field</td>'

    text += '  </tr>\n'

    return text


def prev_next_link(prev, has_next, state_filter, limit, offset, default_limit):
    href = False
    if prev:
        label = 'Prev'
        if offset:
            new_offset = max(offset - limit, 0)
            href = True
    else:
        label = 'Next'
        if has_next:
            new_offset = offset + limit
            href = True

    if href:
        link = '<a href="?cmd=status&filter=%s' % state_filter
        if new_offset:
            link += "&offset=%d" % new_offset
        if limit != default_limit:
            link += "&limit=%d" % limit
        link += '">' + label + '</a>'
    else:
        link = label

    return link


def job_table(db_obj, state_filter, limit, offset, default_limit, max_limit,
              cmd_filter):
    data, has_next = db_obj.get_job_table(state_filter, limit,
                                          offset, cmd_filter)

    link_prev = prev_next_link(True, has_next, state_filter, limit,
                               offset, default_limit)

    link_next = prev_next_link(False, has_next, state_filter, limit,
                               offset, default_limit)

    text = link_prev + '&#160;' + link_next + '\n'

    text += '<table class="wikitable" style="text-align:right;margin-left:auto;margin-right:auto;">\n'
    global job_table_field
    text += table_header(job_table_field)
    for d in data:
        text += to_html(d, job_table_field)

    text += '</table>\n'

    return text, data


def accounting_table(db_obj, jobs, state_filter,
                     limit, offset, default_limit, max_limit):
    job_ids = [x['job_id'] for x in jobs]

    # FIXME: offset/limit not correct, we must have separate offset/limit
    # than the job table offset/limit.
    data, has_next = db_obj.get_accounting_table(limit, 0, job_ids)

    global accounting_table_field

    link_prev = prev_next_link(True, has_next, state_filter, limit,
                               offset, default_limit)

    link_next = prev_next_link(False, has_next, state_filter, limit,
                               offset, default_limit)

    text = link_prev + '&#160;' + link_next + '\n'

    text += '<table class="wikitable" style="text-align:right;margin-left:auto;margin-right:auto;">\n'

    text += table_header(accounting_table_field)

    for d in data:
        text += to_html(d, accounting_table_field)

    text += '</table>\n'

    return text


def handle_status(params, start_response):
    default_limit = 50
    max_limit = 1000

    state_filter = params.get('filter', '')
    cmd_filter = params.get('cmd_filter', None)
    limit = get_int_param(params, 'limit', default_limit, max_limit)
    offset = get_int_param(params, 'offset', 0, None)
    # log(params)

    db_obj = sge_jobs.DbJob()

    text = common_html.get_head('hocr', css='shared.css') + '\n  <body>\n'

    html, jobs = job_table(db_obj, state_filter, limit, offset,
                           default_limit, max_limit, cmd_filter)
    text += html

    text += accounting_table(db_obj, jobs, state_filter, limit, offset,
                             default_limit, max_limit)

    text += '  </body>\n</html>'

    start_response('200 OK', [('Content-Type',
                               'text/html; charset=UTF-8'),
                              ('Content-Length', str(len(text))),
                              ('Access-Control-Allow-Origin', '*')])
    return [text]


def gen_hocr_request(params):
    job_req = {
        'jobname': 'hocr',
        'run_cmd': 'python',
        'args': [
            os.path.expanduser('~/phe/hocr/hocr.py'),
            '-lang:' + params['lang'],
            '-book:' + params['book']
        ],
        'max_vmem': 1024,
    }
    db_obj = sge_jobs.DbJob()

    db_obj.add_request(**job_req)


def handle_query(params, start_response):
    log(params)

    if params['lang'] and params['book']:
        try:
            ret_code = '200 OK'
            result = hocr.get_hocr(params['lang'], params['book'])
        except:
            utils.print_traceback()
            ret_code = '500 Internal Server Error'
            result = {'error': 1, 'text': ret_code}
    else:
        ret_code = '400 Bad Request'
        result = {'error': 1, 'text': ret_code}

    try:
        text = json.dumps(result)
    except UnicodeDecodeError:
        log(result)
        ret_code = '400 Bad Request'
        text = json.dumps({'error': 1, 'text': ret_code})

    start_response(ret_code, [('Content-Type',
                               'application/json' + '; charset=UTF-8'),
                              ('Content-Length', str(len(text))),
                              ('Access-Control-Allow-Origin', '*')])
    return [text]


def myapp(environ, start_response):
    params = query_params(environ)

    if params['cmd'] == 'ping':
        return handle_ping(start_response)
    elif params['cmd'] == 'hocr':
        return handle_query(params, start_response)
    else:
        return handle_status(params, start_response)


if __name__ == "__main__":
    sys.stderr = open(os.path.expanduser('~/log/hocr_cgi.err'), 'a')

    from flup.server.cgi import WSGIServer

    try:
        WSGIServer(myapp).run()
    except BaseException:
        utils.print_traceback()
