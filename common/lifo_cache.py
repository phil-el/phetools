#!/usr/bin/python
# -*- coding: utf-8 -*-

# A simple lifo cache backing up object on disk, when starting ordering
# of item is random. Doesn't support multiple reader/writer.

from collections import OrderedDict
import os
import utils
import sys
import types

# FIXME: add a params to ctor to allow transparent compression.
class LifoCache():
    def __init__(self, cache_name, mem_cache_size = 4, disk_cache_size = 32):
        self.cache_dir = '/data/project/phetools/cache/' + cache_name + '/'
        self.disk_cache = OrderedDict()
        self.mem_cache = OrderedDict()
        if mem_cache_size > disk_cache_size:
            raise ValueError("LifoCache: mem_cache_size > disk_cache_size")
        self.disk_cache_size = disk_cache_size
        self.mem_cache_size = mem_cache_size
        self.cache_access = 0
        self.mem_access_hit = 0
        self.disk_read_hit = 0
        self.disk_write_hit = 0
        for filename in os.listdir(self.cache_dir):
            if len(self.disk_cache) == self.disk_cache_size:
                os.unlink(self.cache_dir + filename)
            else:
                self.disk_cache[filename] = None

    def get(self, filename):
        if type(filename) == types.UnicodeType:
            filename = filename.encode('utf-8')
        data = None
        self.cache_access += 1
        if filename in self.disk_cache.keys():
            if filename in self.mem_cache:
                data = self.mem_cache[filename]
                if data:
                    self.mem_access_hit += 1
                del self.mem_cache[filename]
            del self.disk_cache[filename]
            if not data:
                # FIXME: this is racy, Actually we don't allow multiple
                # reader/writer but someone can remove the file between
                # the check and the read...
                if os.path.exists(self.cache_dir + filename):
                    self.disk_read_hit += 1
                    data = utils.load_obj(self.cache_dir + filename)
            if data:
                self.disk_cache[filename] = True
                if len(self.mem_cache) == self.mem_cache_size:
                    self.mem_cache.popitem(last = False)
                self.mem_cache[filename] = data

        return data

    def set(self, filename, obj):
        if type(filename) == types.UnicodeType:
            filename = filename.encode('utf-8')
        if filename in self.disk_cache:
            del self.disk_cache[filename]
        if filename in self.mem_cache:
            del self.mem_cache[filename]
        if len(self.disk_cache) == self.disk_cache_size:
            old_filename = self.disk_cache.popitem(last = False)[0]
            os.unlink(self.cache_dir + old_filename)
        if len(self.mem_cache) == self.mem_cache_size:
            self.mem_cache.popitem(last = False)
        self.mem_cache[filename] = obj
        self.disk_cache[filename] = True
        self.disk_write_hit += 1
        utils.save_obj(self.cache_dir + filename, obj)

    def stat_ratio(self, count):
        result = 1.0
        if self.cache_access:
            result = (float(self.cache_access) - count) / self.cache_access
        return 1.0 - result

    # convenience, allowed params are 'html' or 'str' all other value
    # will return raw data.
    def access_stat(self, as_type = None):
        mem_hit = self.stat_ratio(self.mem_access_hit)
        disk_read_hit = self.stat_ratio(self.disk_read_hit)
        disk_write_hit = self.stat_ratio(self.disk_write_hit)
        if as_type == 'str' or as_type == 'html':
            format_dict = {
                'mem cache size' : len(self.mem_cache),
                'disk cache size' : len(self.disk_cache),
                'nr access' : self.cache_access,
                'mem hit ratio' : mem_hit * 100,
                'disk hit ratio' : disk_read_hit * 100,
                'disk write ratio' : disk_write_hit * 100, 
                'total hit ratio' : (mem_hit + disk_read_hit) * 100
                }
            result = """mem cache size:\t\t\t%(mem cache size)7d
disk cache size:\t\t%(disk cache size)7d
nr access:\t\t\t%(nr access)7d
mem_hit ratio:\t\t\t%(mem hit ratio)7.2f%%
disk hit ratio:\t\t\t%(disk hit ratio)7.2f%%
disk write hit:\t\t\t%(disk write ratio)7.2f%%
mem_hit ratio + disk_hit ratio:\t%(total hit ratio)7.2f%%""" % format_dict
            if as_type == 'html':
                # FIXME: mis aligned in html... perhaps using another format
                # string? or wrap result in a <pre>?</pre>
                result = result.replace('\n', '<br />\n')
            return result
        else:
            return len(self.mem_cache), len(self.disk_cache),  self.cache_access, mem_hit, disk_read_hit, disk_write_hit

if __name__ == "__main__":
    import random
    import sys
    base_dir = '/data/project/phetools/cache/'
    cache_name = 'test_lifo_cache'
    lifo_cache = LifoCache(cache_name, 31, 32)

    for i in range(1000):
        test_nr = random.randint(0, 32)
        data = lifo_cache.get(str(test_nr))
        if not data:
            lifo_cache.set(str(test_nr), test_nr)

    # expected, 1000 access, mem_hit around 90%, disk_hit around 6%,
    # write_hit around 6%, mem + disk hit around 99.5%
    if len(sys.argv) > 1:
        print lifo_cache.access_stat(sys.argv[1])
    else:
        print lifo_cache.access_stat('str')
