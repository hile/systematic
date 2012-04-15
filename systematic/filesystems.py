#!/usr/bin/env python
"""
Parse filesystem mount information to Mountpoints class
"""

import sys

OS_FILESYSTEM_CLASSES = {
    'darwin':   'systematic.darwin.filesystems',
    'linux2':   'systematic.linux.filesystems',
    'freebsd8': 'systematic.freebsd.filesystems',
}

class FileSystemError(Exception):
    """
    Exception raised when parsing system mount points
    """
    def __str__(self):
        return self.args[0]

class FileSystemFlags(dict):
    """
    Dictionary class to represent mount point mount flags
    """
    def __init__(self,flags=None):
        dict.__init__(self)
        if flags:
            for k in flags:
                self.__setitem__(k,None)

    def __getattr__(self,flag):
        if flag == 'owner':
            if self.has_key('owner'):
                return self['owner']
            else:
                return None
        try:
            return self[flag]
        except KeyError:
            return False

    def set(self,flag,value=True): 
        if self.has_key(flag):
            raise ValueError('Flag already set: %s' % flag)
        self.__setitem__(flag,value)

class MountPoint(dict):
    def __init__(self,device,mountpoint,filesystem):
        dict.__init__(self)
        self['device'] = device
        self['mountpoint'] = mountpoint
        self['filesystem'] = filesystem
        self['flags'] = FileSystemFlags()
    
    def __getattr__(self,item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError('No such MountPoint attribute: %s' % item)

    def __repr__(self):
        return self.mountpoint

class MountPoints(object):
    def __init__(self):
        try:
            model = OS_FILESYSTEM_CLASSES[sys.platform]
            m = __import__(model,globals(),fromlist=[model.split('.')[-1]])
            self.mp = getattr(m,'MountPoints')()
        except KeyError:
            raise ValueError('System type not supported: %s' % sys.platform)
        self.mp.update()

    def __iter__(self):
        return iter(sorted(self.values()))

    def keys(self):
        return self.mp.keys()

    def items(self):
        return self.mp.items()

    def values(self):
        return self.mp.values()

if __name__ == '__main__':
    m = MountPoints()
    for k,v in m.items():
        try:
            print k,v.mountpoint,v.usage['free']
        except FileSystemError,e:
            print e

