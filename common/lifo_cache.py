#!/usr/bin/python

# A simple lifo cache backing up object on disk, when starting ordering
# of item is random. Doesn't support multiple reader/writer.

import thread
from collections import OrderedDict
import os
import utils
import sys
import types


class LifoCacheMem(object):
    def __init__(self, cache_size):
        self._lock = thread.allocate_lock()
        self.cache_size = cache_size
        self.cache = OrderedDict()
        self.read_count = 0
        self.hit_count = 0
        self.write_count = 0

    def get(self, key):
        data = None
        with self._lock:
            self.read_count += 1
            if key in self.cache:
                self.hit_count += 1
                data = self.cache[key]
                del self.cache[key]
                self.cache[key] = data
        return data

    def set(self, key, data):
        with self._lock:
            self.write_count += 1
            if key in self.cache:
                del self.cache[key]
            if len(self.cache) == self.cache_size:
                self.cache.popitem(last=False)
        self.cache[key] = data

    def stat_ratio(self, count, total=None):
        if total is None:
            total = self.read_count
        with self._lock:
            result = 1.0
            if total:
                result = (float(total) - count) / total
        return 1.0 - result

    # convenience, allowed params are 'html' or 'str' all other value will
    # return raw data.
    def access_stat(self, as_type=None):
        hit = self.stat_ratio(self.hit_count)
        if as_type == 'str' or as_type == 'html':
            format_dict = {
                'cache size': len(self.cache),
                'read access': self.read_count,
                'write access': self.write_count,
                'hit ratio': hit * 100,
            }
            result = """\
mem cache size:\t\t%(cache size)7d
read access:\t\t%(read access)7d
write access:\t\t%(write access)7d
hit ratio:\t\t%(hit ratio)7.2f%%""" % format_dict
            if as_type == 'html':
                # FIXME: mis aligned in html... perhaps using another format
                # string? or wrap result in a <pre>?</pre>
                result = result.replace('\n', '<br />\n')
            return result
        else:
            return len(self.cache), self.read_count, self.write_count, hit


# FIXME: add a params to ctor to allow transparent compression.
class LifoCache(LifoCacheMem):
    def __init__(self, cache_name, mem_cache_size=4, disk_cache_size=32):
        super(LifoCache, self).__init__(mem_cache_size)
        if mem_cache_size > disk_cache_size:
            raise ValueError("LifoCache: mem_cache_size > disk_cache_size")
        self.disk_cache_dir = os.path.expanduser('~/cache/') + cache_name + '/'
        self.disk_cache_size = disk_cache_size
        self.disk_cache = OrderedDict()
        self.disk_read_hit = 0
        self.disk_read_count = 0
        self.disk_write_count = 0
        self._disk_lock = thread.allocate_lock()
        for filename in os.listdir(self.disk_cache_dir):
            if len(self.disk_cache) == self.disk_cache_size:
                os.unlink(self.disk_cache_dir + filename)
            else:
                self.disk_cache[filename] = None

    def get(self, filename):
        with self._disk_lock:
            if type(filename) == types.UnicodeType:
                filename = filename.encode('utf-8')
            data = super(LifoCache, self).get(filename)
            if not data:
                self.disk_read_count += 1
                if filename in self.disk_cache:
                    if os.path.exists(self.disk_cache_dir + filename):
                        self.disk_read_hit += 1
                        data = utils.load_obj(self.disk_cache_dir + filename)
                    del self.disk_cache[filename]
                    if data:
                        self.disk_cache[filename] = True
                        super(LifoCache, self).set(filename, data)
        return data

    def set(self, filename, data):
        with self._disk_lock:
            if type(filename) == types.UnicodeType:
                filename = filename.encode('utf-8')
            self.disk_write_count += 1
            if filename in self.disk_cache:
                del self.disk_cache[filename]
            if len(self.disk_cache) == self.disk_cache_size:
                old_filename = self.disk_cache.popitem(last=False)[0]
                os.unlink(self.disk_cache_dir + old_filename)

            self.disk_cache[filename] = True
            utils.save_obj(self.disk_cache_dir + filename, data)
            super(LifoCache, self).set(filename, data)

    def access_stat(self, as_type=None):
        result = super(LifoCache, self).access_stat(as_type)
        hit = self.stat_ratio(self.disk_read_hit, self.disk_read_count)
        if as_type == 'str' or as_type == 'html':
            format_dict = {
                'disk cache size': len(self.disk_cache),
                'read access': self.disk_read_count,
                'write access': self.disk_write_count,
                'hit ratio': hit * 100,
            }
            result1 = """
disk cache size:\t%(disk cache size)7d
read access:\t\t%(read access)7d
write access:\t\t%(write access)7d
hit ratio:\t\t%(hit ratio)7.2f%%""" % format_dict
            if as_type == 'html':
                # FIXME: mis aligned in html... perhaps using another format
                # string? or wrap result in a <pre>?</pre>
                result1 = result1.replace('\n', '<br />\n')
            return result + result1
        else:
            return result[0], result[1], result[2], result[3], len(
                self.disk_cache), self.disk_read_count, self.disk_write_count, hit


if __name__ == "__main__":
    import random

    base_dir = os.path.expanduser('~/cache/')
    cache_name = 'test_lifo_cache'
    lifo_cache = LifoCache(cache_name, 31, 32)

    for i in range(1000):
        test_nr = random.randint(0, 32)
        data = lifo_cache.get(str(test_nr))
        if not data:
            lifo_cache.set(str(test_nr), test_nr)

    # expected, 1000 access, mem_hit around 90%, disk_hit around 6%,
    # write_hit around 6%, mem + disk hit around 96.5%
    if len(sys.argv) > 1:
        print lifo_cache.access_stat(sys.argv[1])
    else:
        print lifo_cache.access_stat('str')
