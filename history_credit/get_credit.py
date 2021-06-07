import os
import sys

sys.path.append(os.path.expanduser('~/wikisource'))
import ws_namespaces as namespaces
from common import db


def default_userdict(count=0):
    # credits are returned in a dict with user name associated with this value
    return {'count': count, 'flags': []}


def get_source_ns(domain, family):
    return namespaces.namespaces[family][domain]


def get_index_ns(domain, family):
    return namespaces.index[family][domain]


def get_page_ns(domain, family):
    return namespaces.page[family][domain]


def prefix_index(cursor, start, ns, max_count=5000):
    count = 0
    last = start
    cont = True
    while cont:
        cursor.execute("""SELECT page_title, page_id
                          FROM page
                          WHERE page_namespace = %s AND page_title >= %s
                          ORDER BY page_title LIMIT 500
                       """,
                       [ns, last])
        for r in cursor.fetchall():
            count += 1
            if not r[0].startswith(start) or count > max_count:
                cont = False
                break
            last = r[0]
            yield r


def get_rev_actor(cursor, rev_ids):
    if len(rev_ids):
        rev_id_str = [str(x) for x in rev_ids]
        q = """SELECT rev_actor
               FROM revision
               WHERE rev_page IN (%s)
            """ % (",".join(rev_id_str),)
        cursor.execute(q)
        for r in cursor.fetchall():
            if r[0] is not None:
                yield r


def get_user_id(cursor, actor_ids):
    actor_id_str = [str(x) for x in actor_ids]
    q = """SELECT actor_user
           FROM actor
           WHERE actor_id IN (%s)
        """ % (",".join(actor_id_str),)
    cursor.execute(q)
    for r in cursor.fetchall():
        if r[0] is not None:
            yield r


def get_user_groups(cursor, actor_ids):
    if len(actor_ids):
        # user_groups table can't be accessed with an actor_id
        actor_id_str = [str(x[0]) for x in get_user_id(cursor, actor_ids)]
        q = """SELECT actor_id, ug_group
               FROM actor, user, user_groups
               WHERE user_id IN (%s) AND ug_user = user_id AND actor_user = user_id
            """ % (','.join(actor_id_str))
        cursor.execute(q)
        for r in cursor.fetchall():
            yield r


def get_user_names(cursor, actor_ids):
    if len(actor_ids):
        actor_id_str = [str(x) for x in actor_ids]
        cursor.execute("""SELECT actor_id, actor_name
                       FROM actor
                       WHERE actor_id IN (%s)
                       """ % (','.join(actor_id_str)))
        for x in cursor.fetchall():
            yield x


def merge_contrib(a, b):
    for key in b:
        a.setdefault(key, default_userdict())
        a[key]['count'] += b[key]['count']
        for flag in b[key]['flags']:
            if not flag in a[key]['flags']:
                a[key]['flags'].append(flag)


def book_pages_id(cursor, book, page_ns):
    book = book.replace(' ', '_')
    pages_id = [x[1] for x in prefix_index(cursor, book + '/', page_ns)]
    return pages_id


def credit_from_pages_id(cursor, pages_id):
    actor_ids = {}
    for x in get_rev_actor(cursor, pages_id):
        actor_ids.setdefault(x[0], 0)
        actor_ids[x[0]] += 1

    user_groups = {}
    for r in get_user_groups(cursor, actor_ids):
        user_groups.setdefault(r[0], [])
        user_groups[r[0]].append(r[1])

    results = {}
    for r in get_user_names(cursor, actor_ids):
        results[r[1]] = {'count': actor_ids[r[0]], 'flags': []}
        if r[0] in user_groups:
            results[r[1]]['flags'] = user_groups[r[0]]

    return results


def get_book_credit(domain, family, cursor, book, ns):
    book = book.replace(' ', '_')
    page_ns = ns[get_page_ns(domain, family)]
    pages_id = book_pages_id(cursor, book, page_ns)
    return credit_from_pages_id(cursor, pages_id)


def get_page_id(cursor, ns_nr, pages):
    fmt_strs = ','.join(['%s'] * len(pages))
    cursor.execute("""SELECT page_id
                      FROM page
                      WHERE page_namespace = %s AND page_title IN (%s)
                      """ % ('%s', fmt_strs),
                   [ns_nr] + list(pages))
    for r in cursor.fetchall():
        yield r


def get_pages_credit(cursor, pages, ns):
    splitted = {}
    for p in pages:
        p = p.replace(' ', '_')
        namespace = p.split(':', 1)
        ns_nr = 0
        if namespace[0] in ns and len(namespace) > 1:
            p = namespace[1]
            ns_nr = ns[namespace[0]]
        splitted.setdefault(ns_nr, [])
        splitted[ns_nr].append(p)

    pages_id = []
    for ns_nr in splitted:
        for r in get_page_id(cursor, ns_nr, splitted[ns_nr]):
            pages_id.append(r[0])

    return credit_from_pages_id(cursor, pages_id)


def get_images_credit_db(cursor, images):
    if len(images):
        fmt_strs = ','.join(['%s'] * len(images))
        cursor.execute("""SELECT img_actor
                          FROM image
                          WHERE img_name IN (%s)
                       """ % fmt_strs,
                       images)
        for r in cursor.fetchall():
            yield r

        cursor.execute("""SELECT oi_actor
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

    images = [x.replace(' ', '_') for x in images]

    conn = db.create_conn(domain='commons', family='wiki')
    common_cursor = db.use_db(conn, 'commons', 'wiki')
    temp = []
    for r in get_images_credit_db(common_cursor, images):
        temp.append(r[0])
    results = [x[1] for x in get_user_names(common_cursor, temp)]
    common_cursor.close()
    conn.close()

    temp = []
    for r in get_images_credit_db(cursor, images):
        temp.append(r[0])
    results += [x[1] for x in get_user_names(cursor, temp)]

    return results


def get_credit(domain, family, books, pages, images):
    conn = db.create_conn(domain=domain, family=family)
    ns = get_source_ns(domain, family)
    cursor = db.use_db(conn, domain, family)

    books_name = []
    results = {}
    for book in books:
        contribs = get_book_credit(domain, family, cursor, book, ns)
        merge_contrib(results, contribs)
        books_name.append(get_index_ns(domain, family) + ':' + book)

    contribs = get_pages_credit(cursor, pages + books_name, ns)
    merge_contrib(results, contribs)

    for user_name in get_images_credit(cursor, images):
        results.setdefault(user_name, default_userdict())
        results[user_name]['count'] += 1

    conn.close()
    cursor.close()

    return results


if __name__ == "__main__":
    family = 'wikisource'
    print get_credit('fr', family, [
        "Cervantes - L’Ingénieux Hidalgo Don Quichotte de la Manche, traduction Viardot, 1836, tome 1.djvu"], [], [])
    # this one has hidden user id, check if we handle it correctly
    print get_credit('pl', family, [], ['Strona:Oscar_Wilde_-_De_profundis.djvu/37'], [])
    print get_credit('fr', family, [], [], [
        "Cervantes - L’Ingénieux Hidalgo Don Quichotte de la Manche, traduction Viardot, 1836, tome 1.djvu"])
