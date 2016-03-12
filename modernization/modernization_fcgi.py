#!/usr/bin/python
from flup.server.fcgi_fork import WSGIServer
from modernization_cgi import myapp
import os
import sys

if __name__ == '__main__':
    sys.stderr = open(os.path.expanduser('~/log/modernization_fcgi.err'), 'a', 0)
    prefork_args = {
        'maxRequests' : 100,
        'maxSpare' : 1,
        'minSpare' : 1,
        'maxChildren' : 1
    }
    WSGIServer(myapp, **prefork_args).run()
