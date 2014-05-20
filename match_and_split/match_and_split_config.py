# -*- coding: utf-8 -*-

import socket
import sys
import os

port = 12346

# configuration: to run the daemon on your local box define an alias of the
# wikisource family and do the setup according to this name in
# pywikipedia/families/ by deriving a class Family(wikisource_family.Family):
if socket.gethostname() == 'zaniah':
    sys.path.append("/usr/src/phe/pywikipedia")
    family = 'wikisourcelocal'
    djvulibre_path = ""
    servername_filename = '/usr/src/phe/botpywi/thomasv/public_html/match_and_split.server'
else: # wmflabs
    family = 'wikisource'
    djvulibre_path = "/usr/bin/"
    servername_filename = '/data/project/phetools/match_and_split.server'
