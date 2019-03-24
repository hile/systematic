"""
Common wrapper classes
"""

import os

from systematic.log import Logger


class SortableContainer(object):
    """Sortable containers

    Sort objects by comparing attributes specified in
    tuple self.compare_fields

    List of attributes must match for compared objects or
    comparison will fail.

    """
    compare_fields = ()

    def __cmp_fields__(self, other):
        if self.compare_fields:
            for field in self.compare_fields:
                a = getattr(self, field)
                b = getattr(other, field)
                if a != b:
                    return (a > b) - (a < b)
            return 0
        else:
            if self != other:
                return (self > other) - (self < other)
            else:
                return 0

    def __eq__(self, other):
        return self.__cmp_fields__(other) == 0

    def __ne__(self, other):
        return self.__cmp_fields__(other) != 0

    def __lt__(self, other):
        return self.__cmp_fields__(other) < 0

    def __le__(self, other):
        return self.__cmp_fields__(other) <= 0

    def __gt__(self, other):
        return self.__cmp_fields__(other) > 0

    def __ge__(self, other):
        return self.__cmp_fields__(other) >= 0


class FileSystemError(Exception):
    pass


class FileSystemFlags(dict):
    """
    Dictionary wrapper to represent mount point mount flags
    """
    def __init__(self, flags=None):
        self.log = Logger('filesystems').default_stream

        if isinstance(flags, list):
            for k in flags:
                self.set(k)

        if isinstance(flags, dict):
            for k, v in flags.items():
                self.set(k, v)

    @property
    def owner(self):
        """
        Returns filesystem owner flag or None
        """
        return 'owner' in self and self['owner'] or None

    def get(self, flag):
        """
        Return False for nonexisting flags, otherwise return flag value
        """
        return flag in self and self[flag] or False

    def set(self, flag, value=True):
        """
        Set a filesystem flag
        """
        if flag in self:
            raise ValueError('Flag already set: {0}'.format(flag))

        self.__setitem__(flag, value)


class MountPoint(SortableContainer):
    """
    Abstract class for device mountpoints implemented in OS specific code.
    """
    compare_fields = ('mountpoint', 'device')

    def __init__(self, mountpoints, device, mountpoint, filesystem, flags=None):
        self.log = Logger('filesystems').default_stream
        self.mountpoints = mountpoints
        self.device = device
        self.mountpoint = mountpoint
        self.filesystem = filesystem
        self.flags = FileSystemFlags(flags=flags if flags is not None else {})
        self.usage = {}

    def __repr__(self):
        return '{0} mounted on {1}'.format(self.device, self.path)

    @property
    def is_virtual(self):
        raise NotImplementedError('Implement is_virtual() is child class')

    @property
    def name(self):
        return os.path.basename(self.mountpoint)

    @property
    def path(self):
        return self.mountpoint

    @property
    def size(self):
        try:
            return self.usage['size']
        except KeyError:
            return 0

    @property
    def used(self):
        try:
            return self.usage['used']
        except KeyError:
            return 0

    @property
    def available(self):
        try:
            return self.usage['available']
        except KeyError:
            return 0

    @property
    def free(self):
        try:
            return self.usage['free']
        except KeyError:
            return 0

    @property
    def percent(self):
        try:
            return self.usage['percent']
        except KeyError:
            return 0

    def as_dict(self, verbose=False):
        """Return data as dict

        """
        data = {
            'device': self.device,
            'mountpoint': self.mountpoint,
            'filesystem': self.filesystem,
            'size': self.size,
            'available': self.free,
            'used': self.used,
            'percent': self.percent,
        }
        if verbose:
            data['flags'] = self.flags
        return data
