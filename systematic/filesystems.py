#!/usr/bin/env python
"""
Parse filesystem mount information to Mountpoints class
"""

import os,sys

from systematic.log import Logger,LoggerError

OS_FILESYSTEM_CLASSES = {
    'darwin':   'darwinist.filesystems',
    'linux2':   'penguinist.filesystems',
    'freebsd9': 'ultimatum.filesystems',
}

class FileSystemError(Exception):
    """
    Exception raised when parsing system mount points
    """
    def __str__(self):
        return self.args[0]

class FileSystemFlags(dict):
    """
    Dictionary wrapper to represent mount point mount flags
    """
    def __init__(self,flags=[]):
        self.log = Logger('filesystems').default_stream

        if isinstance(flags,list):
            for k in flags: self.__setitem__(k,None)
        if isinstance(flags,dict):
            self.update(**flags)

    @property
    def owner(self):
        """
        Returns filesystem owner flag or None
        """
        return self.has_key('owner') and self['owner'] or None

    def get(self,flag):
        """
        Return False for nonexisting flags, otherwise return flag value
        """
        if not self.has_key(flag):
            return False
        return self[flag]

    def set(self,flag,value=True):
        """
        Set a filesystem flag
        """
        if self.has_key(flag):
            raise ValueError('Flag already set: %s' % flag)
        self.__setitem__(flag,value)

class MountPoints(object):
    """
    Thin wrapper to load OS specific implementation for mountpoints
    """
    def __init__(self):
        self.log = Logger('filesystems').default_stream
        self.__instance = None
        self.__next = None
        self.__iternames = None

        try:
            model = OS_FILESYSTEM_CLASSES[sys.platform]
        except KeyError:
            raise ValueError('System type not supported: %s' % sys.platform)

        try:
            m = __import__(model,globals(),fromlist=[model.split('.')[-1]])
            self.__instance = getattr(m,'MountPoints')()
            self.__instance.update()
        except ImportError:
            raise FileSystemError('Module for OS not available: %s' % model)

    def __getattr__(self,attr):
        return getattr(self.__instance,attr)

    def __getitem__(self,item):
        """
        Delegate implementation to OS specific class
        """
        return self.__instance[item]

    def __setitem__(self,item,value):
        """
        Delegate implementation to OS specific class
        """
        self.__instance[item] = value

    def __iter__(self):
        return self

    def next(self):
        """
        Iterate detected mountpoints
        """
        if self.__next is None:
            self.__next = 0
            self.__iternames = self.keys()
        try:
            entry = self[self.__iternames[self.__next]]
            self.__next+=1
            return entry
        except IndexError:
            self.__next = None
            self.__iternames = []
            raise StopIteration

    def filter(self,callback=None):
        """
        Return mountpoints matching a callback function
        """
        return [x for x in self if callback(x)]

class MountPoint(object):
    """
    Abstract class for device mountpoints implemented in OS specific code.
    """
    def __init__(self,device,mountpoint,filesystem,flags={}):
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
