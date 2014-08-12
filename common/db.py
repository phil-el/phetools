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
from contextlib import contextmanager

replica_cnf = os.path.expanduser('~/replica.my.cnf')
_db_prefix = None

def user_db_prefix():
    global _db_prefix
    if _db_prefix == None:
        text = utils.read_file(replica_cnf)
        _db_prefix = re.search(".*user='(.*)'.*", text).group(1) + '__'
    return _db_prefix

def database_name(domain, family):
    if family == 'wikisource' and domain in [ 'old', 'www' ]:
        dbname = 'sourceswiki_p'
    else:
        dbname = domain + family + '_p'
    return dbname

def use_db(conn, domain, family, cursor_class = None):
    q = 'use ' + database_name(domain, family)
    cursor = conn.cursor(cursor_class)
    cursor.execute(q)
    return cursor

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

# Base class for user db, only handle open/close + a context manager.
# Creating a UserDb obj doesn't open the db, either use the context manager
# for read/write use or the open/close method for read only use. Note than
# close() doesn't do a commit(), either do it in your code or use the context
# manager.
class UserDb(object):
    def __init__(self, db_name):
        self.db_name = user_db_prefix() + db_name
        self.conn = self.cursor = None

    def open(self):
        self.conn = create_conn(server = 'tools-db')
        self.cursor = self.conn.cursor(MySQLdb.cursors.DictCursor)
        self.cursor.execute('use ' + self.db_name)

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None

@contextmanager
def connection(db_obj):
    db_obj.open()
    try:
        yield
    except:
        db_obj.conn.rollback()
        raise
    else:
        db_obj.conn.commit()
    finally:
        db_obj.close()

if __name__ == "__main__":
    print 'db_prefix:', user_db_prefix()

    conn = create_conn(domain = 'commons', family = 'wiki')
    conn.close()

    conn = create_conn(server = 'tools-db')
    cursor = conn.cursor()
    q = 'use ' + user_db_prefix() + 'sge_jobs'
    cursor.execute(q)
    cursor.close()
    conn.close()

    db = UserDb('sge_jobs')
    db.open()
    db.close()
