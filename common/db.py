# -*- coding: utf-8 -*-
#
# @file db.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import MySQLdb
import os
import utils
import re

replica_cnf = os.path.expanduser('~/replica.my.cnf')
_db_prefix = None

def db_prefix():
    global _db_prefix
    if _db_prefix == None:
        text = utils.read_file(replica_cnf)
        _db_prefix = re.search(".*user='(.*)'.*", text).group(1) + '__'
    return _db_prefix

def create_conn(**kwargs):
    conn_params = {
        'read_default_file' : replica_cnf,
        }
    if kwargs.has_key('domain'):
        domain = kwargs['domain']
        family = kwargs['family']

        if domain in ["old", "-"]:
            domain = 'sourceswiki'
            family = ''
        db_server = domain + family + '.labsdb'
    else:
        db_server = kwargs['server']

    return MySQLdb.connect(host = db_server, **conn_params)

if __name__ == "__main__":
    print 'db_prefix:', db_prefix()

    conn = create_conn(domain = 'commons', family = 'wiki')
    conn.close()

    conn = create_conn(server = 'tools-db')
    cursor = conn.cursor()
    q = 'use ' + db_prefix() + 'sge_jobs'
    cursor.execute(q)
    cursor.close()
    conn.close()
