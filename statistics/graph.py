#!/usr/bin/python3
# workaround if there is no $DISPLAY exported by the env
import matplotlib

matplotlib.use('Agg')
import os
import datetime
import pylab

from common_stat import decode_res

colors = {'total': '#000000',
          'en': 'r',
          'fr': 'b',
          'de': 'g',
          'ca': 'm',
          'it': 'c',
          'hy': '#ff7000',
          'es': '#a08030',
          'no': '#436712',
          'sv': '#ff2073',
          'pl': '#09eaf2',
          'pt': '#0000d0',
          'ru': '#13ee77',
          'da': '#eff000',
          'br': '#d0fff0',
          'vec': '#d0d0d0',
          'sa': '#d0d000',
          'ml': '#00d0d0',
          'te': '#0f0f0f',
          'bn': '#080808',
          }

names = colors.keys()
names = sorted(names)
names.remove("total")

savepath = os.path.expanduser('~/public_html/graphs/')

count_array = {}
for dom in names + ["total"]:
    count = []
    for i in range(10):  count.append(([], []))
    count_array[dom] = count


# all pr val pr_text pr_percent naked all_text

def draw_domain(dom):
    n1 = "Wikisource_-_pages_%s.png" % dom
    n2 = "Wikisource_-_pages_%s.svg" % dom
    fig = pylab.figure(1, figsize=(12, 12))
    ax = fig.add_subplot(111)

    pylab.clf()
    # deprecated
    # pylab.hold(True)
    pylab.grid(True)
    count = count_array[dom]
    pylab.fill_between(count[0][1], 0, count[0][0], facecolor="#ffa0a0")  # red
    pylab.fill_between(count[4][1], 0, count[4][0], facecolor="#b0b0ff")  # blue
    pylab.fill_between(count[3][1], 0, count[3][0], facecolor="#dddddd")  # gray
    pylab.fill_between(count[2][1], 0, count[2][0], facecolor="#ffe867")  # yellow
    pylab.fill_between(count[1][1], 0, count[1][0], facecolor="#90ff90")  # green

    x = range(1)
    b1 = pylab.bar(x, x, color='#ffa0a0')
    b0 = pylab.bar(x, x, color='#dddddd')
    b2 = pylab.bar(x, x, color='#b0b0ff')
    b3 = pylab.bar(x, x, color='#ffe867')
    b4 = pylab.bar(x, x, color='#90ff90')
    pylab.legend([b1[0], b3[0], b4[0], b0[0], b2[0]],
                 ['not proofread', 'proofread', 'validated', 'without text', 'problematic'], loc=2,
                 prop={'size': 'medium'})

    pylab.plot_date(count[0][1], pylab.zeros(len(count[0][1])), 'k-')
    pylab.xlim(min(count[0][1]), max(count[0][1]))
    ax.xaxis.set_major_locator(pylab.YearLocator())
    ax.xaxis.set_major_formatter(pylab.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()

    pylab.title("%s.wikisource.org" % dom, fontdict={'fontsize': 'xx-large'})
    pylab.ylim(0)
    pylab.savefig(savepath + n1)
    pylab.savefig(savepath + n2)

    n1 = "Wikisource_-_texts_%s.png" % dom
    n2 = "Wikisource_-_texts_%s.svg" % dom
    pylab.figure(1, figsize=(12, 12))
    pylab.clf()
    # deprecated
    pylab.hold(True)
    pylab.grid(True)
    count = count_array[dom]
    pylab.fill_between(rm29(dom, count[8][1]), 0, rm29(dom, count[8][0]), facecolor="#b0b0ff")
    pylab.fill_between(rm29(dom, count[7][1]), 0, rm29(dom, count[7][0]), facecolor="#ffa0a0")
    pylab.fill_between(rm29(dom, count[9][1]), 0, rm29(dom, count[9][0]), facecolor="#dddddd")

    x = range(1)
    b1 = pylab.bar(x, x, color='#b0b0ff')
    b2 = pylab.bar(x, x, color='#ffa0a0')
    if dom != 'de':
        pylab.legend([b1[0], b2[0]], ['with scans', 'naked'], loc=3, prop={'size': 'medium'})
    else:
        pylab.legend([b1[0], b2[0]], ['with transclusion (PR2)', 'older system (PR1)'], loc=3, prop={'size': 'medium'})

    pylab.plot_date(rm29(dom, count[8][1]), pylab.zeros(len(rm29(dom, count[8][1]))), 'k-')
    pylab.xlim(min(count[8][1]), max(count[8][1]))
    ax.xaxis.set_major_locator(pylab.YearLocator())
    ax.xaxis.set_major_formatter(pylab.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()

    pylab.title("%s.wikisource.org" % dom, fontdict={'fontsize': 'xx-large'})
    pylab.ylim(0)
    pylab.savefig(savepath + n1)
    pylab.savefig(savepath + n2)


def draw(domlist, index, func, max_y, tick, name, log=False):
    if not log:
        n1 = "Wikisource_-_%s.png" % name
        n2 = "Wikisource_-_%s.svg" % name
    else:
        n1 = "Wikisource_-_%s.log.png" % name
        n2 = "Wikisource_-_%s.log.svg" % name

    fig = pylab.figure(1, figsize=(12, 12))
    ax = fig.add_subplot(111)

    pylab.clf()
    # deprecated
    pylab.hold(True)
    pylab.grid(True)

    for dom in domlist:
        count = count_array[dom][index]
        if func:
            count = func(count, dom)
        if count:
            if not log:
                pylab.plot(count[1], count[0], '-', color=colors[dom], label=dom, linewidth=1.5)
            else:
                pylab.semilogy(count[1], count[0], '-', color=colors[dom], label=dom, linewidth=1.5)
                # pylab.xlabel("Days (since 9-24-2007)")

    ymin, ymax = pylab.ylim()

    pylab.plot_date(count[1], pylab.zeros(len(count[1])), 'k-')
    ax.xaxis.set_major_locator(pylab.YearLocator())
    ax.xaxis.set_major_formatter(pylab.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()

    if not log:
        if max_y:
            ymax = max_y
            pylab.yticks(pylab.arange(0, ymax + 1, tick))

        pylab.ylim(ymin, ymax)
    else:
        pylab.ylim(100, ymax)

    pylab.legend(loc=2, ncol=2, prop={'size': 'medium'})
    pylab.title(name.replace('_', ' '), fontdict={'fontsize': 'xx-large'})
    pylab.savefig(savepath + n1)
    pylab.savefig(savepath + n2)


def add_point(result, xtime, allpages, num_q0, num_q2, num_q3, num_q4, all_texts, pr_texts, disambig_texts):
    # num_q1 = num - (num_q0 + num_q2 + num_q3 + num_q4 )

    if allpages:
        result[0][0].append(allpages)
        result[0][1].append(xtime)

    if num_q4:
        result[1][0].append(num_q4)
        result[1][1].append(xtime)

    if num_q4 and num_q3:
        result[2][0].append(num_q4 + num_q3)
        result[2][1].append(xtime)

    if num_q2:
        result[3][0].append(num_q4 + num_q3 + num_q0)
        result[3][1].append(xtime)

    if num_q0:
        result[4][0].append(num_q4 + num_q3 + num_q2 + num_q0)
        result[4][1].append(xtime)

    if pr_texts:
        pr_percent = pr_texts * 100. / (all_texts - disambig_texts)
        result[5][0].append(pr_texts)
        result[5][1].append(xtime)
        result[6][0].append(pr_percent)
        result[6][1].append(xtime)
        result[7][0].append(all_texts - (pr_texts + disambig_texts))
        result[7][1].append(xtime)
        result[8][0].append(all_texts)
        result[8][1].append(xtime)
        result[9][0].append(disambig_texts)
        result[9][1].append(xtime)


# global epoch
epoch = False


def add_rev(line):
    bad_days = {
        'en': range(613, 633),  # hesperian bump
        'sv': [942, 943, 944]}  # misconfiguration

    very_bad_days = range(765, 788 + 1)  # bug after code update
    # there's also the toolserver stopping period
    global epoch
    z_time, res = eval(line)
    t_time = z_time / (60 * 60 * 24)
    if not epoch: epoch = t_time
    mtime = t_time - epoch

    total_allpages = 0
    total_num_q0 = 0
    total_num_q2 = 0
    total_num_q3 = 0
    total_num_q4 = 0
    total_all_texts = 0
    total_pr_texts = total_disambig_texts = 0

    d = pylab.date2num(datetime.datetime.fromtimestamp(z_time))

    all_ok = True

    for dom in res.keys():
        if not dom in names: continue
        count = count_array[dom]
        allpages, num_q0, num_q2, num_q3, num_q4, pr_texts, all_texts, disambig_texts = decode_res(res[dom])
        ok = True
        bd = bad_days.get(dom)
        if bd and int(mtime) in bd: ok = False
        if int(mtime) in very_bad_days: ok = False
        if ok:
            add_point(count, d, allpages, num_q0, num_q2, num_q3, num_q4, all_texts, pr_texts, disambig_texts)

            if allpages: total_allpages += allpages
            if num_q0: total_num_q0 += num_q0
            if num_q2: total_num_q2 += num_q2
            if num_q3: total_num_q3 += num_q3
            if num_q4: total_num_q4 += num_q4
            if all_texts: total_all_texts += all_texts
            if pr_texts: total_pr_texts += pr_texts
            if disambig_texts: total_disambig_texts += disambig_texts
        else:
            all_ok = False

    if all_ok:
        count = count_array["total"]
        add_point(count, d, total_allpages, total_num_q0, total_num_q2, total_num_q3, total_num_q4, total_all_texts,
                  total_pr_texts, total_disambig_texts)


def read_from_file(filename):
    f = open(filename, "r")
    revs = f.readlines()
    f.close()
    for item in revs:
        add_rev(item)


# leaky average
def sg(pp, dom):
    v, t = pp
    n = len(v)
    o = []
    d = 0
    av = 0
    for i in range(n):
        if i == 0:
            av = 0
        else:
            dv = (v[i] - v[i - 1])
            dt = (t[i] - t[i - 1])
            d = dv / dt

            ok = (dt > 0.9 and dt < 1.1)
            if ok:
                av = 0.99 * av + 0.01 * d
                # av = d
                # if abs( d )>500: print dom, int(t[i]), d, dv, dt

        # FIXME: this ignore all negative value from one day to another
        # which can occur if a wiki delete some corrected pages (cpvio trouble
        # prolly), if we don't ingore them a big blank rectangle appear on
        # the bottom of graph for those negative value but the curve itself
        # doesn't show them because of the average code. A better solution
        # will be to set Y-Axis in such way than only positive value
        # set are used to setup the Y-Axis scale.
        if av < 0:
            av = 0
        o.append(av)
    return o, t


# remove first 29 days, because the calculation of nonpr_texts was wrong
def rm29(dom, v):
    if dom != 'da':
        return v[29:]
    else:
        return v


def rm29bis(pp, dom):
    a, b = pp
    if dom == 'da': return (a, b)
    n = 29
    return (a[n:], b[n:])


def main():
    read_from_file(os.path.expanduser('~/public_html/data/new_stats.py'))

    print("totals")

    draw(["total"], 2, sg, 2000, 100, "proofread_pages_per_day_(all_wikisources)")
    draw(["total"], 1, sg, 800, 100, "validated_pages_per_day_(all_wikisources)")

    print("per day")

    draw(names, 2, sg, 900, 30, "proofread_pages_per_day")
    draw(names, 1, sg, 340, 20, "validated_pages_per_day")
    draw(names, 0, None, False, 100000, "all_pages")
    draw(names, 2, None, False, 40000, "proofread_pages")
    draw(names, 1, None, False, 20000, "validated_pages")
    draw(names, 0, None, False, 50000, "all_pages", True)
    draw(names, 2, None, False, 10000, "proofread_pages", True)
    draw(names, 1, None, False, 5000, "validated_pages", True)

    draw(names, 5, None, False, 10000, "pr_texts")
    draw(names, 6, rm29bis, 100, 5, "pr_percent")

    draw(['fr'], 7, rm29bis, False, 500, "nonpr_texts_fr")
    draw(['it'], 7, rm29bis, False, 500, "nonpr_texts_it")
    draw(['en'], 7, rm29bis, False, 500, "nonpr_texts_en")
    draw(['de'], 7, rm29bis, False, 500, "nonpr_texts_de")
    draw(['pl'], 7, rm29bis, False, 500, "nonpr_texts_pl")

    print("domains")

    for dom in names:
        draw_domain(dom)

    print("creating thumbnails")
    os.system(os.path.expanduser('~/phe/statistics/mkthumbs'))


if __name__ == "__main__":
    main()
