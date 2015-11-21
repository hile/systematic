"""
Parse filesystem mount information to MountPoints class

Requires external modules from split OS specific modules
"""

import os
import sys
import fnmatch

from systematic.log import Logger, LoggerError


class MountPoints(list):
    """
    Thin wrapper to load OS specific implementation for mountpoints
    """
    def __init__(self):
        if sys.platform[:5] == 'linux':
            from systematic.platform.linux.filesystems import load_mountpoints
            self.loader = load_mountpoints

        elif sys.platform == 'darwin':
            from systematic.platform.darwin.filesystems import load_mountpoints
            self.loader = load_mountpoints

        elif fnmatch.fnmatch(sys.platform, 'freebsd*'):
            from systematic.platform.bsd.filesystems import load_mountpoints
            self.loader = load_mountpoints

        else:
            raise ValueError('MountPoints loader for OS not available: {0}'.format(sys.platform))

        self.update()

    def __getitem__(self, name):
        """
        Delegate implementation to OS specific class
        """
        for mountpoint in self:
            if mountpoint == name:
                return mountpoint
        return None

    def update(self):
        self.__delslice__(0, len(self))
        self.extend(self.loader())
        self.sort()

    @property
    def devices(self):
        return [mountpoint.device for mountpoint in self if hasattr(mountpoint, 'device')]

    @property
    def paths(self):
        return [mountpoint.path for mountpoint in self if hasattr(mountpoint, 'path')]

    def filter(self, callback):
        """
        Return mountpoints matching a callback function
        """
        return [mountpoint for mountpoint in self if callback(mountpoint)]

