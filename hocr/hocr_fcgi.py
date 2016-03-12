#!/usr/bin/python
from flup.server.fcgi_fork import WSGIServer
from hocr_cgi import myapp
import os
import sys

if __name__ == '__main__':
    sys.stderr = open(os.path.expanduser('~/log/hocr_fcgi.err'), 'a', 0)
    prefork_args = {
        'maxRequests' : 100,
        'maxSpare' : 2,
        'minSpare' : 1,
        'maxChildren' : 2
    }
    WSGIServer(myapp, **prefork_args).run()
