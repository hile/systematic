"""
Common wrapper classes
"""


from systematic.log import Logger, LoggerError


class SortableContainer(object):
    """Sortable containers 

    Sort objects by comparing attributes specified in 
    tuple self.compare_fields

    List of attributes must match for compared objects or
    comparison will fail.

    """

    compare_fields = ()
    
    def __cmp__(self, other):
        if self.compare_fields:
            for field in self.compare_fields:
                a = getattr(self, field)
                b = getattr(other, field)
                if a != b:
                    return cmp(a, b)

            return 0

        return cmp(self, other)

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __ne__(self, other):
        return self.__cmp__(other) != 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0


class FileSystemError(Exception):
    pass


class FileSystemFlags(dict):
    """
    Dictionary wrapper to represent mount point mount flags
    """
    def __init__(self,flags=[]):
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

    def get(self,flag):
        """
        Return False for nonexisting flags, otherwise return flag value
        """
        return flag in self and self[flag] or False

    def set(self,flag,value=True):
        """
        Set a filesystem flag
        """
        if self.has_key(flag):
            raise ValueError('Flag already set: %s' % flag)

        self.__setitem__(flag, value)


class MountPoint(SortableContainer):
    """
    Abstract class for device mountpoints implemented in OS specific code.
    """
    compare_fields = ('mountpoint', 'device')

    def __init__(self, device, mountpoint, filesystem, flags={}):
        self.log = Logger('filesystems').default_stream
        self.device = device
        self.mountpoint = mountpoint
        self.filesystem = filesystem
        self.flags = FileSystemFlags(flags=flags)

    def __repr__(self):
        return '%s mounted on %s' % (self.device,self.path)

    @property
    def name(self):
        return os.path.basename(self.mountpoint)

    @property
    def path(self):
        return self.mountpoint

    @property
    def usage(self):
        raise NotImplementedError('Implement usage() is child class')


class MountPoints(list):
    def __getitem__(self, item):
        for entry in self:
            if entry.path == item:
                return entry
        raise KeyError('No such mountpoint: %s' % item)

    def __setitem__(self, item):
        raise NotImplementedError('MountPoints is readonly')

    @property 
    def devices(self):
        return [x.device for x in self]

    @property 
    def paths(self):
        return [x.path for x in self]

    def filter(self, callback):
        """
        Return mountpoints matching a callback function
        """
        return [x for x in self if callback(x)]
