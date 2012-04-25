#!/usr/bin/env python
"""
Parse filesystem mount information to Mountpoints class
"""

import os,sys

OS_FILESYSTEM_CLASSES = {
    'darwin':   'darwinist.filesystems',
    'linux2':   'penguinist.linux.filesystems',
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
        """
        Set a filesystem flag
        """
        if self.has_key(flag):
            raise ValueError('Flag already set: %s' % flag)
        self.__setitem__(flag,value)

class MountPoints(object):
    """
    Thin wrapper to load OS specific module for mountpoints
    """
    def __init__(self):
        try:
            model = OS_FILESYSTEM_CLASSES[sys.platform]
            m = __import__(model,globals(),fromlist=[model.split('.')[-1]])
            mp = getattr(m,'MountPoints')()
            self.mp = mp
            self.mp.update()
        except KeyError:
            raise ValueError('System type not supported: %s' % sys.platform)
        self.__next = None
        self.__iternames = None

    def __getattr__(self,attr):
        """
        Delegate implementation to OS specific class
        """
        return getattr(self.mp,attr)

    def __setattr__(self,attr,value):
        """
        Delegate implementation to OS specific class
        """
        if attr in ['mp','__next','__iternames']:
            object.__setattr__(self,attr,value)
        else:
            return setattr(self.mp,attr,value)

    def __getitem__(self,item):
        """
        Delegate implementation to OS specific class
        """
        return self.mp[item]

    def __setitem__(self,item,value):
        """
        Delegate implementation to OS specific class
        """
        self.mp[item] = value

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

class MountPoint(object):
    """
    Parent class for device mountpoints created in OS specific code.
    Do not call directly.
    """
    def __init__(self,device,mountpoint,filesystem):
        self.device = device
        self.mountpoint = mountpoint
        self.filesystem = filesystem
        self.flags = FileSystemFlags()

    def __getattr__(self,attr):
        if attr == 'name':
            return os.path.basename(self.mountpoint)
        if attr == 'usage':
            return self.checkusage()
        if attr in ['mountpoint','path']:
            return self.mountpoint
        raise AttributeError('No such MountPoint attribute: %s' % attr)

    def __repr__(self):
        return '%s mounted on %s' % (self.device,self.path)

    def checkusage(self):
        """
        Parse and return filesystem usage info as dictionary.
        Must be implemented in child classes
        """
        raise NotImplementedError('Implement checkusage() is child class')

