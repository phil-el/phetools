# -*- coding: utf-8 -*-

import MySQLdb
import os
import sys

def default_userdict(count = 0):
    # credits are returned in a dict with user name associated with this value
    return { 'count' : count, 'flags' : [] }

def database_name(domain, family):
    if family == 'wiksource' and domain == 'old':
        dbname = 'sourceswiki_p'
    else:
        dbname = domain + family + '_p'
    return dbname

def get_source_ns(conn, domain, family):
    dbname = database_name(domain, family)

    cursor = conn.cursor()
    cursor.execute('use toolserver')

    cursor.execute("""SELECT ns_name, ns_id
                      FROM namespacename
                      WHERE dbname = %s
                   """,
                   [ dbname ] )
    result = {}
    for r in cursor.fetchall():
        result[r[0]] = r[1]
    return result

def use_db(conn, domain, family):
    q = 'use ' + database_name(domain, family)
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
    if len(rev_ids):
        rev_id_str = [str(x) for x in rev_ids ]
        q = """SELECT rev_user
               FROM revision
               WHERE rev_page IN (%s)
            """ % ( ",".join(rev_id_str), )
        cursor.execute(q)
        for r in cursor.fetchall():
            yield r

def get_username(cursor, user_ids):
    if len(user_ids):
        user_id_str = [str(x) for x in user_ids ]
        q = """SELECT user_name, ug_group, user_id
               FROM user, user_groups
               WHERE user_id IN (%s) AND ug_user = user_id
            """ % (','.join(user_id_str)) 
        cursor.execute(q)
        for r in cursor.fetchall():
            yield r

def merge_contrib(a, b):
    for key in b:
        a.setdefault(key, default_userdict())
        a[key]['count'] += b[key]['count']
        for flag in b[key]['flags']:
            if not flag in a[key]['flags']:
                a[key]['flags'].append(flag)

def book_pages_id(cursor, book, ns):
    book = book.replace(' ', '_')
    pages_id = [ x[1] for x in prefix_index(cursor, book + '/', ns['Page']) ]
    return pages_id

def credit_from_pages_id(cursor, pages_id):
    user_ids = {}
    for x in get_revision(cursor, pages_id):
        user_ids.setdefault(x[0], 0)
        user_ids[x[0]] += 1

    results = {}
    for x in get_username(cursor, user_ids):
        results.setdefault(x[0], { 'count' : user_ids[x[2]], 'flags' : [] } )
        results[x[0]]['flags'].append(x[1])
    return results

def get_book_credit(cursor, book, ns):
    book = book.replace(' ', '_')
    pages_id = book_pages_id(cursor, book, ns)
    return credit_from_pages_id(cursor, pages_id)

def get_page_id(cursor, ns_nr, pages):
    fmt_strs = ','.join(['%s'] * len(pages))
    cursor.execute("""SELECT page_id
                      FROM page
                      WHERE page_namespace = %s AND page_title IN (%s)
                      """ % ('%s', fmt_strs),
                   [ ns_nr ] + list(pages) )
    for r in cursor.fetchall():
        yield r

def get_pages_credit(cursor, pages, ns):
    splitted = {}
    for p in pages:
        p = p.replace(' ', '_')
        namespace = p.split(':', 1)
        ns_nr = 0
        if namespace[0] in ns:
            p = namespace[1]
            ns_nr = ns[namespace[0]]
        splitted.setdefault(ns_nr, [])
        splitted[ns_nr].append(p)

    pages_id = []
    for ns_nr in splitted:
        for r in get_page_id(cursor, ns_nr, splitted[ns_nr]) :
            pages_id.append(r[0])

    return credit_from_pages_id(cursor, pages_id)

def get_images_credit_db(cursor, images):
    if len(images):
        fmt_strs = ','.join(['%s'] * len(images))
        cursor.execute("""SELECT img_user_text
                          FROM image
                          WHERE img_name IN (%s)
                       """ % fmt_strs,
                       images)
        for r in cursor.fetchall():
            yield r

        cursor.execute("""SELECT oi_user_text
                          FROM oldimage
                          WHERE oi_name IN (%s)
                       """ % fmt_strs,
                       images)
        for r in cursor.fetchall():
            yield r

# cursor is the cursor to the local DB
def get_images_credit(cursor, images):
    if not len(images):
        return []

    images = [ x.replace(' ', '_') for x in images ]
    results = []

    conn = create_conn('commons', 'wiki', 4)
    use_db(conn, 'commons', 'wiki')
    for r in get_images_credit_db(conn.cursor(), images):
        results.append(r[0])
    conn.close()

    for r in get_images_credit_db(cursor, images):
        results.append(r[0])

    return results

def get_credit(domain, family, books, pages, images):
    conn = create_conn(domain, family, 3)
    ns = get_source_ns(conn, domain, family)
    cursor = use_db(conn, domain, family)

    books_name = []
    results = {}
    for book in books:
        contribs = get_book_credit(cursor, book, ns)
        merge_contrib(results, contribs)
        books_name.append('Index:' + book )

    contribs = get_pages_credit(cursor, pages + books_name, ns)
    merge_contrib(results, contribs)

    # FIXME, we don't get flags for user not already in the results
    for user_name in get_images_credit(cursor, images):
        results.setdefault(user_name, default_userdict())
        results[user_name]['count'] += 1

    return results

def cluster_from_domain(conn, domain, family):
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT server
                   FROM toolserver.wiki
                   WHERE dbname = %s
                   """,
                   [ database_name(domain, family)])
    return cursor.fetchone()[0]

# hint can be used by application to get directly the right cluster
def create_conn(domain, family, hint):
    conn_params = {
        'user' : 'phe',
        'read_default_file' : os.path.expanduser("~/.my.cnf"),
        }
    conn = MySQLdb.connect(host = 'sql-s%s' % hint, **conn_params)
    cluster = cluster_from_domain(conn, domain, family)
    if cluster != hint:
        conn.close()
        # FIXME: log it somewhere, caller application would prolly redirect
        # sys.stderr to a log file
        #print >> sys.stderr, "bad hint, expect %d found %d" % (hint, cluster)
        conn = MySQLdb.connect(host = 'sql-s%d' % cluster, **conn_params)
    return conn

if __name__ == "__main__":
    domain = 'fr'
    conn = create_conn(domain, 'wikisource', 3)
    for arg in sys.argv[1:]:
        get_credit(conn, domain, [ arg ])
