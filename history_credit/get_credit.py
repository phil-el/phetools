# -*- coding: utf-8 -*-

import MySQLdb
import os
import sys

def use_db(conn, name):
    if name != 'old':
        q= "use " + name + "wikisource_p;"
    else:
        q = "use sourceswiki_p"
    cursor = conn.cursor()
    cursor.execute(q)
    return cursor

def prefixed_name(book, cursor, max_count = 5000):
    count = 0
    last = book
    cont = True
    while cont:
        q = "SELECT page_title, page_id FROM page WHERE page_namespace = 104 AND page_title >= '" + last + "' ORDER BY page_title LIMIT 500;"
        cursor.execute(q)
        for r in cursor.fetchall():
            count += 1
            if not r[0].startswith(book) or count > max_count:
                cont = False
                break
            last = r[0]
            yield r

def get_revision(conn, ids, cursor):
    id_str = [str(x) for x in ids ]
    q = 'select rev_user from revision where rev_page = ' + ' OR rev_page = '.join(id_str)
    cursor.execute(q)
    for r in cursor.fetchall():
        yield r

def get_username(conn, user_ids, cursor):
    user_id_str = [str(x) for x in user_ids ]
    q = 'select user_name from user where user_id = ' + ' OR user_id = '.join(user_id_str)
    cursor.execute(q)
    for r in cursor.fetchall():
        yield r

def get_credit(conn, book, domain = 'fr'):
    book = book.replace(' ', '_')
    cursor = use_db(conn, domain)
    ids = [ x[1] for x in prefixed_name(book, cursor) ]
    user_ids = set([r[0] for r in get_revision(conn, ids, cursor)])
    return [ x for x in get_username(conn, user_ids, cursor) ]
    #for r in get_username(conn, user_ids, cursor):
    #    print r

def create_conn(domain = 'fr'):
    conn = MySQLdb.connect(host = "sql-s3", user = "phe",
                           read_default_file=os.path.expanduser("~/.my.cnf"))
    return conn

if __name__ == "__main__":
    conn = create_conn()
    for arg in sys.argv[1:]:
        get_credit(conn, arg)
