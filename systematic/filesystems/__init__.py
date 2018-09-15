"""
Parse filesystem mount information to MountPoints class

Example usage:

from systematic.filesystems import MountPoints
mp = MountPoints()

"""

import sys
import fnmatch


class FilesystemError(Exception):
    pass


class MountPoints(list):
    """Mountpoints for this OS

    Loads OS specific implementation of mountpoints
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
            raise FilesystemError('MountPoints loader for OS not available: {0}'.format(sys.platform))

        self.update()

    def __getitem__(self, item):
        """Get item for mountpoint

        Delegate implementation to OS specific class
        """
        # Return by index
        if isinstance(item, int):
            return super(MountPoints, self).__getitem__(item)

        # Return by device or path
        for mountpoint in self:
            if mountpoint.device == item:
                return mountpoint

            if mountpoint.path == item:
                return mountpoint

        return None

    def update(self):
        """Update mountpoints

        """
        del self[0:len(self)]
        self.extend(self.loader(self))
        self.sort()
        return self

    @property
    def devices(self):
        """Return devices

        """
        return [mountpoint.device for mountpoint in self if hasattr(mountpoint, 'device')]

    @property
    def paths(self):
        """Return mount paths

        """
        return [mountpoint.path for mountpoint in self if hasattr(mountpoint, 'path')]

    def filter(self, callback):
        """Filter with callback

        Return mountpoints matching a callback function
        """
        return [mountpoint for mountpoint in self if callback(mountpoint)]
