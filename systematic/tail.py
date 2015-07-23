"""
Python implementation of 'tail' type file reader class
"""

import os
import time

INTERVAL = 0.01

class TailReaderError(Exception):
    pass


class TailReader(object):
    def __init__(self, path=None, fd=None):
        self.path = path
        self.stat = None
        self.fd = fd
        self.pos = 0

    def __iter__(self):
        return self

    def __format_line__(self, line):
        """Format line

        Format entry returned by readline. Override in subclass to parse
        entries automatically: default version just returns provided value

        """
        return line

    def next(self):
        return self.readline()

    def close(self):
        if self.fd is not None:
            self.fd.close()
        self.fd = None
        self.stat = None

    def load(self):
        """Load file

        Load file to self.fd

        """
        if self.fd is not None:
            self.close()

        if not os.path.isfile(self.path):
            raise TailReaderError('No such file: {0}'.format(self.path))

        if not os.access(self.path, os.R_OK):
            self.stat = None
            self.fd = None
            self.pos = 0
            raise TailReaderError('Permission denied: {0}'.format(self.path))

        try:
            self.fd = open(self.path, 'r')
            self.stat = os.stat(self.path)
            self.fd.seek(0)
            self.pos = 0
            self.year = time.localtime(self.stat.st_mtime).tm_year

        except IOError, (ecode, emsg):
            raise TailReaderError('Error opening {0}: {1}'.format(self.path, emsg))
        except OSError, (ecode, emsg):
            raise TailReaderError('Error opening {0}: {1}'.format(self.path, emsg))

    def seek_to_end(self):
        """Jump to end of file

        Instead of reading lines in file before tailing, use this to jump to end
        of file after initializing and you'll get the new entries on the fly.

        """
        if self.fd is None:
            self.load()
        self.fd.seek(os.stat(self.path).st_size)

    def readline(self):
        """Read a line from the file

        Read a line from the file. If no input is available, blocks waiting for
        data.

        If file is removed or truncated and re-created, reopens the file handle
        automatically.
        """

        while True:
            try:
                if self.stat is not None and os.stat(self.path).st_ino != self.stat.st_ino:
                    self.close()

                if self.fd is not None:
                    if self.pos > 0 and self.pos > os.stat(self.path).st_size:
                        self.load()

            except IOError, (ecode, emsg):
                self.close()
            except OSError, (ecode, emsg):
                self.close()

            if self.fd is None:
                self.load()

            if self.fd is not None:
                try:
                    line = self.fd.readline()

                    if line != '':
                        return self.__format_line__(line[:-1])

                except IOError, (ecode, emsg):
                    raise TailReaderError('Error opening {0}: {1}'.format(self.path, emsg))
                except OSError, (ecode, emsg):
                    raise TailReaderError('Error opening {0}: {1}'.format(self.path, emsg))

                try:
                    self.pos = self.fd.tell()

                except IOError, (ecode, emsg):
                    raise TailReaderError('Error reading {0}: {1}'.format(self.path, emsg))
                except OSError, (ecode, emsg):
                    raise TailReaderError('Error reading {0}: {1}'.format(self.path, emsg))

            time.sleep(INTERVAL)
