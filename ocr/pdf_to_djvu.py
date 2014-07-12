# -*- coding: utf-8 -*-
#
# @file pdf_to_djvu.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import utils
import subprocess
import resource
import os
import sys

djvulibre_path = ''
gsdjvu = os.path.expanduser('~/root/gsdjvu/bin/gs')

def setrlimits():
    resource.setrlimit(resource.RLIMIT_AS, (1<<29, 1<<29))
    resource.setrlimit(resource.RLIMIT_CORE, (1<<27, 1<<27))
    resource.setrlimit(resource.RLIMIT_CPU, (60*60, 60*60))

def pdf_to_djvu(in_file):

    if type(in_file) == type(u''):
        in_file = in_file.encode('utf-8')

    if gsdjvu:
        os.environ['GSDJVU'] = gsdjvu

    out_file = in_file[:-3] + 'djvu'

    djvudigital = djvulibre_path + 'djvudigital'
    # --words option is useless as many pdf contains text layer only for
    # the first page
    ls = subprocess.Popen([ djvudigital, "--dpi=300", in_file, out_file], stdout=subprocess.PIPE, preexec_fn=setrlimits, close_fds = True)
    text = utils.safe_read(ls.stdout)
    if text:
        print text
    ls.wait()
    if ls.returncode != 0:
        print >> sys.stderr, "djvudigital fail: ", ls.returncode, in_file
        out_file = None

    if gsdjvu:
        del os.environ['GSDJVU']

    return out_file


if __name__ == "__main__":
    in_file = 'https://upload.wikimedia.org/wikipedia/commons/8/81/Accord_compl%C3%A9mentaire_relatif_%C3%A0_la_Malaisie_le_11_Septembre_1963.pdf'
    out_file = os.path.expanduser('~/tmp/')  + 'Accord complémentaire relatif à la Malaisie le 11 Septembre 1963.pdf'
    utils.copy_file_from_url(in_file, out_file)
    djvu_name = pdf_to_djvu(out_file)
    os.remove(out_file)
    #os.remove(djvu_name)
