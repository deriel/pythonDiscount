# Based on https://code.activestate.com/recipes/576642/
import pickle
import os
import shutil


class PersistentDict(dict):
    ''' Persistent pickle dictionary with an API compatible with shelve and anydbm.

    The dict is kept in memory, so the dictionary operations run as fast as
    a regular dictionary.

    Write to disk is delayed until close or sync (similar to gdbm's fast mode).
    '''

    def __init__(self, filename, flag='c', mode=None, *args, **kwds):
        self.flag = flag                    # r=readonly, c=create, or n=new
        self.mode = mode                    # None or an octal triple like 0644
        self.filename = filename
        if flag != 'n' and os.access(filename, os.R_OK):
            fileobj = open(filename, 'rb')
            with fileobj:
                self.load(fileobj)
        dict.__init__(self, *args, **kwds)

    def sync(self):
        'Write dict to disk'
        if self.flag == 'r':
            return
        filename = self.filename
        tempname = filename + '.tmp'
        fileobj = open(tempname, 'wb')
        try:
            self.dump(fileobj)
        except Exception:
            os.remove(tempname)
            raise
        finally:
            fileobj.close()
        shutil.move(tempname, self.filename)    # atomic commit
        if self.mode is not None:
            os.chmod(self.filename, self.mode)

    def close(self):
        self.sync()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def dump(self, fileobj):
        pickle.dump(dict(self), fileobj, 2)

    def load(self, fileobj):
        fileobj.seek(0)
        return self.update(pickle.load(fileobj))


if __name__ == '__main__':
    import random

    # Make and use a persistent dictionary
    with PersistentDict('/tmp/demo.db', 'c') as d:
        print(d, 'start')
        d['abc'] = '123'
        d['rand'] = random.randrange(10000)
        print(d, 'updated')

    # Show what the file looks like on disk
    with open('/tmp/demo.db', 'rb') as f:
        print(f.read())
