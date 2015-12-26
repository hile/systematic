"""
Process lists.

Uses custom flags for ps command to get similar output for all supported platforms.
"""

import os
import sys

from datetime import datetime, timedelta
from subprocess import Popen, PIPE
from systematic.classes import SortableContainer


TIME_FORMATS = (
    '%a %b %d %H:%M:%S %Y',
    '%a %d %b %H:%M:%S %Y',
)

PS_FIELDS = (
    'lstart',
    'sess',
    'ppid',
    'pid',
    'ruid',
    'rgid',
    'ruser',
    'vsz',
    'rss',
    'state',
    'tdev',
    'time',
    'command',
)


class ProcessError(Exception):
    pass


class Process(SortableContainer):
    """Process entry

    To sort these properly, keys must include at least 'pid' and 'ruser' or 'user'
    """
    compare_fields = ( 'userid', 'username', 'started', 'pid', )

    def __init__(self, keys, line):

        keys = [x for x in keys]
        lstart_index = keys.index('lstart')
        fields = line.split()

        if lstart_index != -1:
            self.started = self.__parse_date__(' '.join(fields[lstart_index:lstart_index+5]))
            fields = fields[:lstart_index] + fields[lstart_index+5:]
            keys.remove('lstart')
        else:
            self.started = None

        for key in keys:
            if key == 'command':
                value = ' '.join(fields[keys.index(key):])
            else:
                value = fields[keys.index(key)]

            if key not in ( 'ruser', 'user', 'time', 'tdev', 'state', 'command', ):
                try:
                    value = long(value)
                except ValueError:
                    pass

            setattr(self, key, value)

    def __repr__(self):
        return '{0} {1} {2}'.format(self.username, self.pid, self.command)

    def __parse_date__(self, value):
        for fmt in TIME_FORMATS:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                pass
        return None

    @property
    def is_kernel_process(self):
        """Kernel process flag

        Kernel processes are in session 0. If sess is not known, False is returned

        Note: OS/X ps does not show kernel processes like linux and BSDs and sess is always 0
        """
        if sys.platform == 'darwin' or not hasattr(self, 'sess'):
            return False
        return self.sess == 0

    @property
    def userid(self):
        """Sort user ID

        Usually we sort by ruid key, but allow other options as well
        """
        for key in ('ruid', 'uid'):
            if hasattr(self, key):
                return getattr(self, key)
        return None

    @property
    def username(self):
        """Sort username

        Usually we sort by ruser key, but allow other options as well
        """
        for key in ('ruser', 'user'):
            if hasattr(self, key):
                return getattr(self, key)
        return None

    @property
    def realpath(self):
        """Executable real path

        Try to lookup executable realpath for process from /proc filesystem.

        Returns None if /proc is not available or details not readable.
        """
        if not hasattr(self, 'pid'):
            return None

        exe = '/proc/{0}/exe'.format(self.pid)
        if not os.path.islink(exe):
            return None

        try:
            return os.path.realpath(exe)
        except:
            return None


class Processes(list):
    """
    Thin wrapper to load OS specific implementation for process list
    """
    def __init__(self, fields=PS_FIELDS):
        self.update(fields)

    def update(self, fields):
        self.__delslice__(0, len(self))

        cmd =  [ 'ps', '-wwaxo', ','.join(fields) ]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()

        for line in stdout.splitlines()[1:]:
            self.append(Process(fields, line))

        self.sort()

    def sorted_by_field(self, field, reverse=False):
        """Sort processes in-list by given field.

        If reverse is True, the in-line ordering is reversed after sorting.
        """
        results = [entry for entry in sorted(lambda x, y: cmp(getattr(x, field), getattr(y, field)))]
        if reverse:
            results.reverse()
        return results

    def filter(self, *args, **kwargs):
        """Filter entries

        Filters entries matching given filters. Filter must be a
        - list of key=value strings
        - dictionary with valid keys
        """
        filters = []

        try:
            filters = [(k,v) for x in args for k,v in x.split('=', 1)]
        except ValueError, emsg:
            raise ProcessError('Invalid filter list: {0}: {1}'.format(args, emsg))
        filters.extend(kwargs.items())

        filtered = []
        for entry in self:
            matches = True
            for k,v in filters:
                if not hasattr(entry, k):
                    raise ProcessError('Invalid filter key: {0}'.format(k))
                if getattr(entry, k) != v:
                    matches = False
                    break

            if matches:
                filtered.append(entry)

        filtered.sort()
        return filtered
