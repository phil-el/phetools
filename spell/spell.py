# -*- coding: utf-8 -*-
#
# @file spell.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import aspell
import os


class Speller:
    def __init__(self, lang):
        if lang in ['pt', 'pt_BR']:
            data_dir = os.path.expanduser('~/root/tmp/usr/lib64/aspell')
        else:
            data_dir = os.path.expanduser('~/root/usr/lib/aspell')

        self.speller = aspell.Speller(('data-dir', data_dir),
                                      ('dict-dir', data_dir),
                                      ('size', '80'),
                                      ('sug-mode', 'fast'),
                                      ('encoding', 'utf-8'),
                                      ('lang', lang))

    def check(self, word):
        return True if self.speller.check(word.encode('utf-8')) else False

    def suggest(self, word):
        suggest = self.speller.suggest(word.encode('utf-8'))
        return [unicode(x, 'utf-8') for x in suggest]


if __name__ == "__main__":
    import sys

    speller = Speller(sys.argv[1])
    print speller.check(sys.argv[2])
    print speller.suggest(sys.argv[2])
