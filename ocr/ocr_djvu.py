#!/usr/bin/python3
import sys
import os
import ocr
import multiprocessing
from common import utils
import errno
import subprocess
import resource
import re

djvulibre_path = ''


def setrlimits():
    mega = 1 << 20
    resource.setrlimit(resource.RLIMIT_AS, (1536 * mega, 1536 * mega))
    resource.setrlimit(resource.RLIMIT_CORE, (128 * mega, 128 * mega))
    resource.setrlimit(resource.RLIMIT_CPU, (30 * 60, 30 * 60))


def get_nr_pages_djvu(filename):
    djvused = djvulibre_path + 'djvused'
    ls = subprocess.Popen([djvused, "-e", "n", filename], stdout=subprocess.PIPE, preexec_fn=setrlimits, close_fds=True)
    text = utils.safe_read(ls.stdout)
    ls.wait()
    if ls.returncode != 0:
        print("Error: djvused fail to exec", ls.returncode, file=sys.stderr)
        return None
    return int(text)


def image_size(page_nr, filename):
    djvused = djvulibre_path + 'djvused'
    ls = subprocess.Popen([djvused, "-e", "select %d; size" % page_nr, filename], stdout=subprocess.PIPE,
                          preexec_fn=setrlimits, close_fds=True)
    text = utils.safe_read(ls.stdout)
    ls.wait()
    if ls.returncode != 0:
        print("Error: djvused fail to exec", ls.returncode, file=sys.stderr)
        return None

    match = re.search(r'width=(\d+) height=(\d+)', text)
    return int(match.group(1)), int(match.group(2))


def extract_image(opt, page_nr, filename):
    try:
        width, height = image_size(page_nr, filename)

        subsample = 1
        while (width * height) // subsample > (1 << 20) * 50:
            subsample += 1

        subsample = min(subsample, 12)
    except Exception:
        utils.print_traceback("Unable to get image size, subsample=1", filename)
        subsample = 1

    if subsample != 1:
        print("subsample", subsample)

    tiff_name = f'{opt.temp_tiff_dir}/page_{page_nr:04}.tif'
    ddjvu = djvulibre_path + 'ddjvu'
    ls = subprocess.Popen(
        [ddjvu, "-format=tiff", "-page=%d" % page_nr, "-subsample=%d" % subsample, filename, tiff_name],
        stdout=subprocess.PIPE, preexec_fn=setrlimits, close_fds=True)
    text = utils.safe_read(ls.stdout)
    if text:
        print(text)
    ls.wait()
    if ls.returncode != 0:
        print("extract_image fail: ", ls.returncode, filename, page_nr, file=sys.stderr)
        return None
    return tiff_name


def do_one_page(opt, page_nr, filename):
    tiff_name = extract_image(opt, page_nr, filename)
    if not tiff_name:
        return

    out_filename = f'{opt.out_dir}page_{page_nr:04}'
    if opt.config == 'hocr':
        out_filename += '.hocr'
    else:
        out_filename += '.txt'

    ocr.ocr(tiff_name, f'{opt.out_dir}page_{page_nr:04}', opt.lang, opt.config)
    if opt.compress:
        utils.compress_file(out_filename, out_filename, opt.compress)
        os.remove(out_filename)

    os.remove(tiff_name)


def do_file(job_queue, opt, filename):
    while True:
        page_nr = job_queue.get()
        if page_nr is None:
            print("Stopping thread")
            return
        try:
            do_one_page(opt, page_nr, filename)
        except Exception:
            utils.print_traceback(filename)


def ocr_djvu(opt, filename, task_scheduler=None):
    print("Starting to process:", filename)

    if not opt.out_dir.endswith('/'):
        opt.out_dir += '/'

    nr_pages = get_nr_pages_djvu(filename)
    if nr_pages is None:
        print("unable to get_nr_pages for file:", filename, file=sys.stderr)
        return False

    if opt.num_thread == -1:
        opt.num_thread = multiprocessing.cpu_count()
        if not task_scheduler:
            opt.num_thread = max(int(opt.num_thread // 2), 1)

    if opt.num_thread == 1:
        for nr in range(1, nr_pages + 1):
            if not opt.silent:
                utils.safe_write(sys.stderr, f'{nr}/{nr_pages}\r')
            do_one_page(opt, nr, filename)
    else:
        thread_array = []
        job_queue = multiprocessing.Queue(opt.num_thread)
        args = (job_queue, opt, filename)
        for i in range(opt.num_thread):
            if not opt.silent:
                print("starting thread")
            t = multiprocessing.Process(target=do_file, args=args)
            t.daemon = True
            t.start()
            if task_scheduler:
                task_scheduler.job_started(t)
            thread_array.append(t)

        for nr in range(1, nr_pages + 1):
            if not opt.silent:
                utils.safe_write(sys.stderr, f'{nr}/{nr_pages}\r')
            job_queue.put(nr)

        for i in range(opt.num_thread):
            job_queue.put(None)

        while len(thread_array):
            for i in range(len(thread_array) - 1, -1, -1):
                try:
                    thread_array[i].join()
                    del thread_array[i]
                except OSError as ose:
                    if ose.errno != errno.EINTR:
                        raise ose

        if not opt.silent:
            print("all thread finished")

    if not opt.silent:
        utils.safe_write(sys.stderr, "\n")

    return True


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
    # tiff temp file are the biggest IO, move them to /tmp/$ui_$pid/
    # this assume /tmp is not nfs mounted so this dir name is not racy
    # with other process running on a different exec node.
    options.temp_tiff_dir = f'/tmp/{os.getuid()}_{os.getpid()}'

    if not os.path.exists(options.temp_tiff_dir):
        print("creating temp dir:", options.temp_tiff_dir, file=sys.stderr)
        os.mkdir(options.temp_tiff_dir)

    return options


if __name__ == "__main__":
    options = default_options()

    for arg in sys.argv[1:]:
        if arg == '-help':
            print(sys.argv[0], "dir/djvu_name -config: -lang: -j: -compress")
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

    try:
        os.rmdir(options.temp_tiff_dir)
    except:
        print("unable to remove directory:", options.temp_tiff_dir, file=sys.stderr)
