# -*- coding: utf-8 -*-

import MySQLdb
import os
import sys

def database_name(domain):
    if domain in [ '', 'www', 'old' ]:
        dbname = 'sourceswiki_p'
    else:
        dbname = domain + 'wikisource_p'
    return dbname

def get_source_ns(conn, domain):
    dbname = database_name(domain)

    cursor = conn.cursor()
    cursor.execute('use toolserver')

    cursor.execute("""SELECT ns_name, ns_id
                      FROM namespacename
                      WHERE dbname = %s AND (ns_name = %s OR ns_name = %s)
                   """,
                   [ dbname, 'Page', 'Index' ] )
    result = {}
    for r in cursor.fetchall():
        result[r[0]] = r[1]
    return result

def use_db(conn, domain):
    q = 'use ' + database_name(domain)
    cursor = conn.cursor()
    cursor.execute(q)
    return cursor

def prefix_index(cursor, start, ns, max_count = 5000):
    count = 0
    last = start
    cont = True
    while cont:
        cursor.execute("""SELECT page_title, page_id
                          FROM page
                          WHERE page_namespace = %s AND page_title >= %s
                          ORDER BY page_title LIMIT 500
                       """,
                       [ ns, last ])
        for r in cursor.fetchall():
            count += 1
            if not r[0].startswith(start) or count > max_count:
                cont = False
                break
            last = r[0]
            yield r

def get_revision(cursor, rev_ids):
    rev_id_str = [str(x) for x in rev_ids ]
    q = """SELECT rev_user
           FROM revision
           WHERE rev_page IN (%s)
        """ % ( ",".join(rev_id_str), )
    cursor.execute(q)
    for r in cursor.fetchall():
        yield r

def get_username(cursor, user_ids):
    user_id_str = [str(x) for x in user_ids ]
    q = """SELECT user_name, ug_group, user_id
           FROM user, user_groups
           WHERE user_id IN (%s) AND ug_user = user_id
        """ % (','.join(user_id_str)) 
    cursor.execute(q)
    for r in cursor.fetchall():
        yield r

def get_credit(conn, domain, book):
    book = book.replace(' ', '_')
    ns = get_source_ns(conn, domain)
    cursor = use_db(conn, domain)
    rev_ids = [ x[1] for x in prefix_index(cursor, book + '/', ns['Page']) ]

    user_ids = {}
    for x in get_revision(cursor, rev_ids):
        user_ids.setdefault(x[0], 0)
        user_ids[x[0]] += 1

    results = {}
    for x in get_username(cursor, user_ids):
        results.setdefault(x[0], { 'count' : user_ids[x[2]], 'flags' : [] } )
        results[x[0]]['flags'].append(x[1])
    return results

def create_conn(domain):
    conn = MySQLdb.connect(host = "sql-s3", user = "phe",
                           read_default_file=os.path.expanduser("~/.my.cnf"))
    return conn

if __name__ == "__main__":
    domain = 'fr'
    conn = create_conn(domain)
    for arg in sys.argv[1:]:
        get_credit(conn, domain, arg)
