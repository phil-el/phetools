#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import ocr
import multiprocessing
import utils
import traceback
import errno
import subprocess
import resource

djvulibre_path = ''

def setrlimits():
    resource.setrlimit(resource.RLIMIT_AS, (1<<30, 1<<30))
    resource.setrlimit(resource.RLIMIT_CORE, (1<<27, 1<<27))
    resource.setrlimit(resource.RLIMIT_CPU, (30*60, 30*60))

# FIXME: all read/write must be protected against EINTR
def get_nr_pages_djvu(filename):
    djvused = djvulibre_path + 'djvused'
    ls = subprocess.Popen([ djvused, "-e", "n", filename], stdout=subprocess.PIPE, preexec_fn=setrlimits, close_fds = True)
    text = utils.safe_read(ls.stdout)
    ls.wait()
    if ls.returncode != 0:
        print "Error: djvused fail to exec", ls.returncode
        return None
    return int(text)

def extract_image(opt, page_nr, filename):
    tiff_name = opt.out_dir + 'page_%04d.tif' % page_nr
    ddjvu = djvulibre_path + 'ddjvu'
    ls = subprocess.Popen([ ddjvu, "-format=tiff", "-page=%d" % page_nr, filename, tiff_name], stdout=subprocess.PIPE, preexec_fn=setrlimits, close_fds = True)
    text = utils.safe_read(ls.stdout)
    if text:
        print text
    ls.wait()
    if ls.returncode != 0:
        print >> sys.stderr, "extract_image fail: ", ls.returncode
        return None
    return tiff_name

def do_one_page(opt, page_nr, filename):
    tiff_name = extract_image(opt, page_nr, filename)
    if not tiff_name:
        return

    ocr.ocr(tiff_name, opt.out_dir + 'page_%04d' % page_nr, opt.lang, opt.config)

    if opt.compress:
        filename = opt.out_dir + "page_%04d" % page_nr
        if opt.config == 'hocr':
            filename += '.html'
        else:
            filename += '.txt'

        utils.compress_file(filename, filename, opt.compress)
        os.remove(filename)

    os.remove(tiff_name)

def do_file(job_queue, opt, filename):
    while True:
        page_nr = job_queue.get()
        if page_nr == None:
            print "Stopping thread"
            return
        try:
            do_one_page(opt, page_nr, filename)
        except Exception, e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            try:
                print >> sys.stderr, 'TRACEBACK'
                print >> sys.stderr, filename
                traceback.print_exception(exc_type, exc_value, exc_tb)
            finally:
                del exc_tb

def ocr_djvu(opt, filename, task_scheduler = None):

    fd = open('/home/phe/wsbot/log/tesseract.log', 'a')
    print >> fd, "Starting to process:", filename
    fd.close()

    if not opt.out_dir.endswith('/'):
        opt.out_dir += '/'

    nr_pages = get_nr_pages_djvu(filename)
    if nr_pages == None:
        print >> sys.stderr, "unable to get_nr_pages for file:", filename
        return 1

    if opt.num_thread == -1:
        opt.num_thread = multiprocessing.cpu_count()
        if not task_scheduler:
            opt.num_thread = max(int(opt.num_thread/2), 1)

    if opt.num_thread == 1:
        for nr in range(1, nr_pages + 1):
            if not opt.silent:
                utils.safe_write(sys.stderr, str(nr) + '/' + str(nr_pages) + '\r')
            do_one_page(opt, nr, filename)
    else:
        thread_array = []
        job_queue = multiprocessing.Queue(opt.num_thread)
        args = (job_queue, opt, filename)
        for i in range(opt.num_thread):
            if not opt.silent:
                print "starting thread"
            t = multiprocessing.Process(target=do_file, args=args)
            t.daemon = True
            t.start()
            if task_scheduler:
                task_scheduler.job_started(t)
            thread_array.append(t)

        for nr in range(1, nr_pages + 1):
            if not opt.silent:
                utils.safe_write(sys.stderr, str(nr) + '/' + str(nr_pages) + '\r')
            job_queue.put(nr)

        for i in range(opt.num_thread):
            job_queue.put(None)

        while len(thread_array):
            for i in range(len(thread_array) - 1, -1, -1):
                try:
                    thread_array[i].join()
                    del thread_array[i]
                except OSError, ose:
                    if ose.errno != errno.EINTR:
                        raise ose

        if not opt.silent:
            print "all thread finished"

    if not opt.silent:
        utils.safe_write(sys.stderr, "\n")

    return 0

def default_options():
    class Options:
        pass

    options = Options()
    options.config = ''
    options.num_thread = 1
    options.base_files = []
    options.compress = None
    options.silent = False
    options.out_dir = './'

    return options

if __name__ == "__main__":

    options = default_options()

    for arg in sys.argv[1:]:
        if arg == '-help':
            print sys.argv[0], "dir/djvu_name -config: -lang: -j: -compress"
            sys.exit(1)
        elif arg.startswith('-config:'):
            options.config = arg[len('-config:'):]
        elif arg.startswith('-lang:'):
            options.lang = arg[len('-lang:'):]
        elif arg.startswith('-j:'):
            options.num_thread = int(arg[len('-j:'):])
        elif arg.startswith('-compress:'):
            options.compress = arg[len('-compress:'):]
        else:
            options.base_files.append(arg)


    for filename in options.base_files:
        path = os.path.split(filename)
        options.out_dir = path[0]
        ocr_djvu(options, filename)
