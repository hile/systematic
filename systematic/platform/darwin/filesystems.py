#!/usr/bin/env python
"""
Abstraction of filesystem mount points for OS X
"""

import os
import re
from systematic.classes import check_output, CalledProcessError

from mactypes import Alias

from systematic.classes import MountPoint, FileSystemFlags, FileSystemError
from systematic.platform.darwin.diskutil import DiskInfo, DiskUtilError

re_mountpoint = re.compile(r'([^\s]*) on (.*) \(([^\)]*)\)$')
re_df = re.compile(r'^([^\s]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%\s+(.*)$')

PSEUDO_FILESYSTEMS = (
    'devfs',
)

class OSXMountPoint(MountPoint):
    """
    One OS X mountpoint parsed from /sbin/mount output

    Extra attributes:
    hfspath     Returns OS X 'hfs path' or None
    """
    def __init__(self, mountpoint, device=None, filesystem=None):
        super(OSXMountPoint, self).__init__(device, mountpoint, filesystem)

        try:
            self.hfspath = Alias(self.mountpoint).hfspath
        except ValueError:
            self.hfspath = None

        self.diskinfo = {}
        if os.access(self.device, os.R_OK):
            self.update_diskinfo()

    @property
    def is_virtual(self):
        return self.filesystem in PSEUDO_FILESYSTEMS

    @property
    def name(self):
        if self.diskinfo.has_key('VolumeName'):
            return self.diskinfo['VolumeName']
        return os.path.basename(self.mountpoint)

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
    def percent(self):
        try:
            return self.usage['percent']
        except KeyError:
            return 0

    @property
    def writable(self):
        if self.diskinfo.has_key('Writable'):
            return self.diskinfo['Writable']
        return False

    @property
    def bootable(self):
        if self.diskinfo.has_key('Bootable'):
            return self.diskinfo['Bootable']
        return False

    @property
    def internal(self):
        if self.diskinfo.has_key('Internal'):
            return self.diskinfo['Internal']
        return False

    @property
    def ejectable(self):
        if self.diskinfo.has_key('Ejectable'):
            return self.diskinfo['Ejectable']
        return True

    @property
    def removable(self):
        if self.diskinfo.has_key('Removable'):
            return self.diskinfo['Removable']
        return False

    @property
    def blocksize(self):
        if self.diskinfo.has_key('DeviceBlockSize'):
            return self.diskinfo['DeviceBlockSize']
        return 0

    @property
    def usage(self):
        """
        Check usage percentage for this mountpoint.
        Returns dictionary with usage details.
        """
        try:
            output = check_output(['df', '-k', self.mountpoint])
        except CalledProcessError,e:
            raise FileSystemError('Error checking filesystem usage: {0}'.format(e))

        header, usage = output.split('\n', 1)
        m = re_df.match(usage)
        if not m:
            raise FileSystemError('Error matching df output line: {0}'.format(usage))

        return {
            'mountpoint': self.mountpoint,
            'size': long(m.group(2)),
            'used': long(m.group(3)),
            'free': long(m.group(4)),
            'percent': int(m.group(5))
        }

    def update_diskinfo(self):
        """Update DiskInfo object

        Only available if user has read access to raw device

        """
        self.diskinfo = DiskInfo(self.device)


def load_mountpoints():
    """
    Update mount points from /sbin/mount output
    """
    mountpoints = []

    try:
        output = check_output(['/sbin/mount'])
    except CalledProcessError, e:
        raise FileSystemError('Error getting mountpoints: {0}'.format(e))

    for l in [l for l in output.split('\n') if l.strip() != '']:
        if l[:4] == 'map ':
            continue

        m = re_mountpoint.match(l)
        if not m:
            continue

        device = m.group(1)
        mountpoint = m.group(2)
        flags = map(lambda x: x.strip(), m.group(3).split(','))
        filesystem = flags[0]
        flags = flags[1:]

        entry = OSXMountPoint(mountpoint, device, filesystem)

        for f in flags:
            if f[:11] == 'mounted by ':
                entry.flags.set('owner', f[11:])
            else:
                entry.flags.set(f, True)

        mountpoints.append(entry)

        return mountpoints
