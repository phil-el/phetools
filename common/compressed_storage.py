#
# @file compressed_storage.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import utils


class CompressedStorage():
    def __init__(self, filename):
        self.base_path = "/".join(filename.split('/')[:-1])
        self.index = utils.load_obj(filename + '.index')
        self.fd_data = open(filename)

    def data(self, key):
        compress, data = self.raw_data(key)

        if compress == 'bz2':
            import bz2
            data = bz2.decompress(data)
        elif compress == 'gzip':
            import zlib
            data = zlib.decompress(data)
        elif compress:
            raise ValueError("unknown compression method: " + compress)

        return data

    def raw_data(self, key):
        item = self.index['items'][key]

        self.fd_data.seek(item['offset'])

        compress = self.index['compress']
        if item.has_key('compress'):
            compress = item['compress']

        return compress, self.fd_data.read(item['size'])

    def extra_data(self, key):
        return self.index['items'][key].get('extra_data', None)

    def close(self):
        self.fd_data.close()


class CompressedStorageBuilder():
    # use compress = None to default to no compression
    def __init__(self, filename, compress='bz2'):
        self.index = {
            'compress': compress,
            'items': {}
        }
        self.filename = filename
        self.fd_data = open(self.filename, 'w')

    def close(self):
        self.fd_data.close()
        utils.save_obj(self.filename + '.index', self.index)

    # Pass None to avoid compression.
    def add_item(self, key, data, compress='default', extra_data=None):
        if compress == 'default':
            compress = self.index['compress']

        if compress == 'bz2':
            import bz2
            data = bz2.compress(data)
        elif compress == 'gzip':
            import zlib
            data = zlib.compress(data)
        elif compress:
            raise ValueError("unknown compression method: " + compress)

        self.raw_add_item(key, data, compress, extra_data)

    def raw_add_item(self, key, data, compress, extra_data=None):
        self.index['items'][key] = {
            'offset': self.fd_data.tell(),
            'size': len(data)
        }
        if compress != self.index['compress']:
            self.index['items'][key]['compress'] = compress
        if extra_data:
            self.index['items'][key]['extra_data'] = extra_data

        self.fd_data.write(data)


if __name__ == "__main__":
    import sys
    import os

    compress = sys.argv[1]
    builder = CompressedStorageBuilder('test.' + compress, compress)

    base_path = '/usr/src/phe/botpywi/temp/'
    for filename in os.listdir(base_path):
        if filename.endswith('.html'):
            fd_in = open(base_path + filename)
            builder.add_item(filename, fd_in.read())
            fd_in.close()
    builder.close()

    compressed_storage = CompressedStorage('test.' + compress)
    for filename in os.listdir(base_path):
        if filename.endswith('.html'):
            print compressed_storage.data(filename)

    compressed_storage.close()
