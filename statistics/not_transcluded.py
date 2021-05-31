#
# @file transclusions.py
#
# @remark Copyright 2016 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import sys
import os

sys.path.append(os.path.expanduser('~/wikisource'))
from ws_category import domain_urls as urls
from ws_namespaces import index as index_name
from common import db
from gen_stats import all_domain
from common import common_html
import urllib.parse


def filter_result(books):
    result = []
    for key in books:
        # FIXME: is >= 5 ok ?
        page_ids = books[key]
        if len(page_ids) >= 5:
            # FIXME: this is perhaps not the best way as we check for
            # activity only in pages not transcluded, that means someone
            # is perhaps working on pages already transcluded or is working
            # on red page w/o validating them. Another way will be to get the
            # page id of the index and from that use "related changes" filtered
            # to namespace Page:
            fmt_strs = ','.join(['%s'] * len(page_ids))
            cursor.execute("""SELECT count(*)
                              FROM recentchanges
                              WHERE rc_bot=0 AND rc_cur_id IN (%s)
                           """ % fmt_strs,
                           page_ids)

            if not cursor.fetchone()[0]:
                result.append((len(page_ids), key))
            else:
                print("filtered:", key)

            # debug: for replicas missing record
            if False and key == 'Dictionnaire_portatif_de_cuisine,_d’office,_et_de_distillation,_1772.djvu':
                q = 'select page_title from page where page_id in (%s)' % fmt_strs
                cursor.execute(q, page_ids)
                for x in range(cursor.rowcount):
                    print(cursor.fetchone()[0])

    result.sort(reverse=True)

    return result


def format_html_line(domain, bookname, count):
    title = index_name['wikisource'][domain] + ':' + bookname

    if domain == 'old':
        domain = 'mul'

    result = '<li>'

    fmt = '<a href="//%s.wikisource.org/wiki/%s">%s</a> %d'
    result += fmt % (domain, urllib.parse.quote(title), bookname, count)

    # checker redirect with a 301 from checker? to checker/? so use
    # directly that url even if it's a bit weird
    fmt = ' — <a href="https://checker.toolforge.org/?db=%s&title=%s">Check pages</a>'
    result += fmt % (db.database_name(domain, 'wikisource'), title)

    result += '</li>'

    return result


def not_transcluded(domain, cursor):
    # set of Page: in cat 3/4 not transcluded from main
    query = """
SELECT page_title, page_id FROM categorylinks LEFT JOIN page ON page_id=cl_from
    WHERE cl_to in (%s, %s) AND page_title NOT IN
        (SELECT tl_title FROM templatelinks
            WHERE tl_namespace=%s AND tl_from_namespace=0);
"""
    ns = urls[domain][0]
    cat3 = urls[domain][1]
    cat4 = urls[domain][2]
    cursor.execute(query, [cat3, cat4, ns])
    print(cursor.rowcount)
    result = {}
    for x in range(cursor.rowcount):
        title, page_id = cursor.fetchone()
        title = title.decode().split('/')[0]
        if title[-5:] in ['.djvu', '.pdf', '.tif']:
            result.setdefault(title, [])
            result[title].append(page_id)

    result = filter_result(result)

    if False:
        out_file = os.path.expanduser('~/tmp/transclusions/%s.txt' % domain)
        out_fd = open(out_file, 'w')
        for d in result:
            print(d[1], d[0], file=out_fd)
        out_fd.close()

    out_file = os.path.expanduser('~/tmp/transclusions/%s.html' % domain)
    if os.path.exists(out_file):
        os.remove(out_file)

    out_fd = open(out_file, 'w')

    title = '%s.wikisource.org not transcluded page' % domain
    head = common_html.get_head(title, html5=True)  # .encode('utf-8')
    print(head, file=out_fd)
    print('<body>', file=out_fd)
    if len(result):
        print('<ol>', file=out_fd)

        for d in result:
            print(format_html_line(domain, d[1], d[0]), file=out_fd)

        print('</ol>', file=out_fd)
    else:
        print("Empty result, no Index meet the criteria to be listed in this file.", file=out_fd)

    print('\n</body>\n</html>', file=out_fd)
    out_fd.close()

    return len(result)


if __name__ == "__main__":
    tot_count = 0
    for domain in all_domain:
        print(domain)

        # if domain != 'fr':
        #    continue

        conn = db.create_conn(domain=domain, family='wikisource')
        cursor = db.use_db(conn, domain=domain, family='wikisource')

        tot_count += not_transcluded(domain, cursor)

        cursor.close()
        conn.close()
    print("total:", tot_count)
