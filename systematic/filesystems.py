"""
Parse filesystem mount information to MountPoints class

Requires external modules from split OS specific modules
"""

import os
import sys
import fnmatch

from systematic.log import Logger, LoggerError


class MountPoints(object):
    """
    Thin wrapper to load OS specific implementation for mountpoints
    """
    __loader = None
    def __init__(self):
        if MountPoints.__loader is None:
            if sys.platform[:5] == 'linux':
                from systematic.platform.linux.filesystems import LinuxMountPoints
                MountPoints.__loader = LinuxMountPoints()

            elif sys.platform == 'darwin':
                from systematic.platform.darwin.filesystems import OSXMountPoints
                MountPoints.__loader = OSXMountPoints()

            elif fnmatch.fnmatch(sys.platform, 'freebsd*'):
                from systematic.platform.bsd.filesystems import BSDMountPoints
                MountPoints.__loader = BSDMountPoints()

            else:
                raise ValueError('MountPoints loader for OS not available: %s' % sys.platform)

        self.__dict__['_MountPoints__loader'] = MountPoints.__loader
        self.__loader.update()

    def __getattr__(self, attr):
        return getattr(self.__loader, attr)

    def __setattr__(self, attr, value):
        return setattr(self.__loader, attr, value)

    def __getitem__(self, item):
        """
        Delegate implementation to OS specific class
        """
        return self.__loader[item]

    def __setitem__(self, item, value):
        """
        Delegate implementation to OS specific class
        """
        self.__loader[item] = value

    def __iter__(self):
        return self.__loader.__iter__()

    def next(self):
        return self.__loader.next()
