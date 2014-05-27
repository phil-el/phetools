#!/usr/bin/python

import os,codecs
import time, sys

#os.chdir("/home/phe/wsbot")

sys.path.append('/data/project/phetools/wikisource')
from ws_category import domain_urls as urls
from common import decode_res, disambiguations

# The domain name we care.
all_domain = set([
    'old', 'bn',  'br',  'ca',  'da',  'de',  'en',  'el',
    'es',  'et',  'fr',  'gu',  'he',  'hr',  'hu',  'hy',
    'id',  'it',  'la',  'ml',  'nl',  'no',  'pl',  'pt',
    'ru',  'sa',  'sl',  'sv',  'te',  'vec', 'vi',  'zh',
])

def create_conn(domain, family):
    import MySQLdb

    conn_params = {
        'read_default_file' : os.path.expanduser("~/replica.my.cnf"),
        }
    if domain in ["old", "-"]:
        domain = 'sourceswiki'
        family = ''
    db_server = domain + family + '.labsdb'

    return MySQLdb.connect(host = db_server, **conn_params)


def catreq(cat, ns):
    return "select /* SLOW_OK */ count(cl_from) as num from categorylinks where cl_to='%s' and cl_from in (select page_id from page where page_namespace=%d)"%(cat,ns)

def get_stats(domains):

    import urllib
    res = {}

    for dom in domains:
        print dom
        conn = create_conn(dom, 'wikisource')
        cursor = conn.cursor ()
	ns = urls[dom][0]
        if dom!='old':
            q="use "+dom+"wikisource_p;"
        else:
            q="use sourceswiki_p"
	cursor.execute(q)

	q="select /* SLOW_OK */ count(page_id) as num from page where page_namespace=%d and page_is_redirect=0"%ns
	cursor.execute(q)
	row = cursor.fetchone ()
        num_pages = int(row[0])

	if len(urls[dom])>1:
	    cat3 = urllib.unquote(urls[dom][1])
  	    cat4 = urllib.unquote(urls[dom][2])
	    cursor.execute(catreq(cat3,ns))
	    row = cursor.fetchall()[0]
            num_q3 = int(row[0])
	    cursor.execute(catreq(cat4,ns))
	    row = cursor.fetchall()[0]
            num_q4 = int(row[0])
	else:
	    num_q3 = 0
	    num_q4 = 0

	if len(urls[dom])>3:
	    cat0 = urls[dom][3]
  	    cat2 = urls[dom][4]
	    cursor.execute(catreq(cat0,ns))
	    row = cursor.fetchall()[0]
            num_q0 = int(row[0])
	    cursor.execute(catreq(cat2,ns))
	    row = cursor.fetchall()[0]
            num_q2 = int(row[0])
	else:
	    num_q0 = 0
	    num_q2 = 0

	q = "select /* SLOW_OK */ count(distinct tl_from) as num from templatelinks left join page on page_id=tl_from where tl_namespace=%d and page_namespace=0;"%ns
	cursor.execute(q)
	row = cursor.fetchone ()
        num_trans = int(row[0])

	cursor.execute ("select /* SLOW_OK */ count(distinct page_id) from page where page_namespace=0 and page_is_redirect=0;")
	row = cursor.fetchone ()
        num_texts = int(row[0])

        #disambiguation pages
        # first try the __DISAMBIG__ keyword
        cursor.execute("select count(page_title) from page where page_namespace = 0 and page_is_redirect = 0 and page_id in (select pp_page from page_props where pp_propname = 'disambiguation')")
        row = cursor.fetchone ()
        num_disambig = int(row[0])

        if num_disambig == 0:
            #then test if the message is a template...
            q = "select /* SLOW_OK */ count(page_title) from page left join templatelinks on page_id=tl_from where page_namespace=0 and tl_namespace=10 and tl_title in ( select pl_title from page left join pagelinks on page_id=pl_from where pl_namespace=10 and page_namespace=8 and page_title='Disambiguationspage' )"
            cursor.execute (q)
            row = cursor.fetchone ()
            num_disambig = int(row[0])

            if num_disambig==0 and disambiguations.get(dom) :
                q = "select /* SLOW_OK */ count(page_title) from page left join templatelinks on page_id=tl_from where page_namespace=0 and tl_namespace=10 and tl_title='%s'"%disambiguations.get(dom)
                cursor.execute (q)
                row = cursor.fetchone ()
                num_disambig = int(row[0])

        if dom=='no':
            import pywikibot
            qq = "select /* SLOW_OK */ page_title from page where page_namespace=0 and page_is_redirect=0 and page_id not in ( select distinct tl_from from templatelinks left join page on page_id=tl_from where tl_namespace=104 and page_namespace=0 ) and page_id not in ( %s );" % q.replace("count(page_title)","page_id")
            cursor.execute(qq)
            rows = cursor.fetchall()
	    site = pywikibot.getSite(dom,fam='wikisource')
            f = codecs.open('/data/project/phetools/public_html/data/nakedtexts_'+dom+'.html','w',"utf-8")
            f.write("<html><head></head><body>")
            f.write("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />")
            f.write("<b>Naked texts at "+dom+".wikisource.org</b> (%d)</br/>"%len(rows) )
            f.write("<ul>")
            for row in rows:
                pagename = row[0]
                page = pywikibot.Page(site, pagename.decode('utf8'))
                page_path = site.nice_get_address(page.title(asUrl = True))
                page_url = "http://"+dom+".wikisource.org"+page_path
                s="<li><a href=\"%s\">%s</a></li>"%(page_url,page.title())
                f.write(s)
            f.write("</ul>")
            f.write("</body>")
        
        res[dom] = (num_pages, num_q0, num_q2, num_q3, num_q4, num_trans, num_texts, num_disambig)
        
        cursor.close ()
        conn.close ()
    return res
            


def spaced_int(i,sep):
    str = repr(i)[-3:]
    if i>999: 
	str = repr(i)[-6:-3] + sep + str
    if i>999999:
	str = repr(i)[:-6] + sep + str
    return str



def write_templates(res,keys):
    import pywikibot

    for dom in ['fr','en', 'bn']:
	if dom=='fr':
	    sep=' '
	elif dom == 'en':
	    sep=','
        else:
            sep = ''

        num, num_q0, num_q2, num_q3, num_q4, num_tr, num_texts, num_disambig = decode_res( res[dom] )
        percent = num_tr*100./(num_texts-num_disambig)
        num_q1 = num - (num_q0 + num_q2 + num_q3 + num_q4 ) 

	site = pywikibot.getSite(dom,fam='wikisource')
        page = pywikibot.Page(site,"Template:PAGES_NOT_PROOFREAD")
        page.put(spaced_int(num_q1,sep))
        page = pywikibot.Page(site,"Template:ALL_PAGES")
        page.put(spaced_int(num,sep))
        page = pywikibot.Page(site,"Template:PR_TEXTS")
        page.put(spaced_int(num_tr,sep))
        page = pywikibot.Page(site,"Template:ALL_TEXTS")
        page.put(spaced_int(num_texts - num_disambig,sep))
        page = pywikibot.Page(site,"Template:PR_PERCENT")
        page.put("%.2f"%percent)

def read_stats(offset):
    f = open("/data/project/phetools/public_html/data/new_stats.py","r")
    lines = f.readlines()
    f.close()
    t, oldres = eval( lines[offset] )
    for k in oldres.keys():
        oldres[k] = decode_res(oldres[k])
    return t, oldres 

if __name__ == "__main__":

    opt_write = False
    opt_diff  = False
    opt_doms = []
    opt_yesterday = False
    delta = 1
    for arg in sys.argv:
        if arg=="-w":
            opt_write = True
            if len(sys.argv)!=2:
                print "arguments error"
                exit(1)
        if arg=="-d":
            opt_diff = True
        elif arg[0:2]=="-d":
            opt_diff = int(arg[2:])

        if arg in all_domain:
            opt_doms.append(arg)

        if arg=="-y":
            opt_yesterday = True
        elif arg[0:2]=="-y":
            opt_yesterday = True
            delta = int(arg[2:])

    if opt_doms:
	domains = opt_doms
    else:
        domains = all_domain

    if not opt_yesterday:
        res = get_stats(domains)
        stats_time = time.time()
        if opt_diff:
            old_time, oldres = read_stats(-opt_diff)
    else:
        stats_time, res = read_stats(-delta)
        if opt_diff:
            old_time, oldres = read_stats(-delta-opt_diff)

    keys = res.keys()
    keys.sort(lambda x,y: cmp(res[y][3]+2*res[y][4],res[x][3]+2*res[x][4]))

    if opt_write:
        write_templates(res,keys)
        f = open("/data/project/phetools/public_html/data/new_stats.py","a")
        f.write(repr( (time.time() , res ) ) +"\n")
        f.close()
        import graph
        graph.main()
    else:
        if opt_diff:
            diffs = {}
            for i in res.keys() :
                if not i in oldres.keys(): oldres[i] = (0,0,0,0,0,0,1,0)
                diffs[i] = ( res[i][0] - oldres[i][0], \
                           res[i][1] - oldres[i][1], \
                           res[i][2] - oldres[i][2], \
                           res[i][3] - oldres[i][3], \
                           res[i][4] - oldres[i][4], \
                           res[i][5] - oldres[i][5], \
                           res[i][6] - oldres[i][6], \
                           res[i][7] - oldres[i][7] )

	total = total_q0 = total_q1 = total_q2 = total_q3 = total_q4 = 0
        total_tr = total_disambig = total_naked = total_texts = 0

	lines=[]

        if opt_diff:
            print "date: Difference between " + ' '.join(time.ctime(old_time).split()[:3]) + " " + time.ctime(old_time).split()[4] +" and "+' '.join(time.ctime(stats_time).split()[:3]) + ' ' + time.ctime(stats_time).split()[4]
        else:
            print "date: Statistics on " + time.ctime(stats_time)
        print "            all      q1     q2      q0   q3+q4      q4  |     all       pr    naked   disamb   percent"
	for dom in keys:
            #all, pages_q0, pages_q2, proofread, validated, num_tr, num_good, percent = res[dom]
            if opt_diff:
                num, num_q0, num_q2, num_q3, num_q4, num_tr, num_texts, num_disambig =  diffs[dom]
                percent = res[dom][5]*100./(res[dom][6]-res[dom][7]) - oldres[dom][5]*100./(oldres[dom][6]-oldres[dom][7])
            else:
                num, num_q0, num_q2, num_q3, num_q4, num_tr, num_texts, num_disambig =  res[dom] 
                percent = num_tr*100./(num_texts - num_disambig)
                
            num_q1 = num - (num_q0 + num_q2 + num_q3 + num_q4 )
            num_naked = num_texts - num_tr - num_disambig
            

            def str_int(nn,ll=6):
                out = str(nn)
                for i in range(ll-len(str(nn))):  out = " "+out
                return out
                
            sa = str_int(num,7)
            sp0 = str_int(num_q0)
            sp1 = str_int(num_q1)
            sp2 = str_int(num_q2,5)
            sp3 = str_int(num_q3+num_q4)
            sp4 = str_int(num_q4)

	    st = str_int(num_tr)
	    s_disambig = str_int(num_disambig)
	    stt = str_int(num_texts)
	    s_percent = str_int( "%.2f"%percent)
	    s_naked = str_int( num_naked )


            if len(dom)==2: dom=" "+dom
	    lines.append("  "+dom+" : %s  %s  %s  %s  %s  %s  |  %s   %s   %s   %s    %s\n"
                         %(sa, sp1, sp2, sp0, sp3, sp4, stt , st, s_naked, s_disambig, s_percent))

            total    += num
            total_q0 += num_q0
            total_q1 += num_q1
            total_q2 += num_q2
            total_q3 += num_q3
            total_q4 += num_q4
            total_tr += num_tr
            total_disambig += num_disambig
            total_naked += num_naked
            total_texts += num_texts

        out = "".join(lines)
        if len(keys)>1:
	    out = out + "total : %s  %s  %s  %s  %s  %s  |  %s   %s   %s   %s \n"\
                  %( str_int(total,7), str_int(total_q1), str_int(total_q2,5),\
                     str_int(total_q0), str_int(total_q3+total_q4), str_int(total_q4),\
                     str_int(total_texts), str_int(total_tr), str_int(total_naked), str_int(total_disambig) 
                     )

	print out[:-1]
