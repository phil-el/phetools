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
        cursor.execute("""SELECT page_title, page_id
                          FROM page
                          WHERE page_namespace = %s AND page_title >= %s
                          ORDER BY page_title LIMIT 500
                       """,
                       # FIXME: do not hardcode 104 ns number of Page:
                       [ 104, last ])
        for r in cursor.fetchall():
            count += 1
            if not r[0].startswith(book) or count > max_count:
                cont = False
                break
            last = r[0]
            yield r

def get_revision(rev_ids, cursor):
    rev_id_str = [str(x) for x in rev_ids ]
    q = """SELECT rev_user
           FROM revision
           WHERE rev_page IN (%s)
        """ % ( ",".join(rev_id_str), )
    cursor.execute(q)
    for r in cursor.fetchall():
        yield r

def get_username(user_ids, cursor):
    user_id_str = [str(x) for x in user_ids ]
    q = """SELECT user_name, ug_group, user_id
           FROM user, user_groups
           WHERE user_id IN( %s ) AND ug_user = user_id
        """ % (','.join(user_id_str)) 
    cursor.execute(q)
    for r in cursor.fetchall():
        yield r

def get_credit(conn, book, domain = 'fr'):
    book = book.replace(' ', '_')
    cursor = use_db(conn, domain)

    rev_ids = [ x[1] for x in prefixed_name(book, cursor) ]

    user_ids = {}
    for x in get_revision(rev_ids, cursor):
        user_ids.setdefault(x[0], 0)
        user_ids[x[0]] += 1

    results = {}
    for x in get_username(user_ids, cursor):
        results.setdefault(x[0], { 'count' : user_ids[x[2]], 'flags' : [] } )
        results[x[0]]['flags'].append(x[1])
    return results

def create_conn(domain = 'fr'):
    conn = MySQLdb.connect(host = "sql-s3", user = "phe",
                           read_default_file=os.path.expanduser("~/.my.cnf"))
    return conn

if __name__ == "__main__":
    conn = create_conn()
    for arg in sys.argv[1:]:
        get_credit(conn, arg)
