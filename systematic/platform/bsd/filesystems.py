#!/usr/bin/env python
"""
Implementation of FreeBSD filesystem mount point parsing
"""

import os
import re
from systematic.classes import check_output, CalledProcessError

from systematic.log import Logger, LoggerError
from systematic.classes import MountPoint, FileSystemFlags, FileSystemError

PSEUDO_FILESYSTEMS = [
    'procfs',
    'devfs',
    'fdescfs',
]

RE_MOUNT = re.compile(r'([^\s]*) on ([^\s]+) \(([^\)]*)\)$')


class BSDMountPoint(MountPoint):
    """
    One BSD mountpoint based on /sbin/mount output line
    Additional attributes:
    """
    def __init__(self, device, mountpoint, filesystem):
        super(BSDMountPoint, self).__init__(device, mountpoint, filesystem)

    @property
    def is_virtual(self):
        return self.filesystem in PSEUDO_FILESYSTEMS

    @property
    def usage(self):
        """
        Check usage percentage for this mountpoint.
        Returns dictionary with usage details.
        """
        if self.filesystem in PSEUDO_FILESYSTEMS:
            return {}

        try:
            output = check_output(['df','-k',self.mountpoint])
        except CalledProcessError:
            raise FileSystemError('Error getting usage for {0}'.format(self.mountpoint))

        header, usage = output.split('\n', 1)
        try:
            usage = ' '.join(usage.split('\n'))
        except ValueError:
            pass

        fs, size, used, free, percent, mp = map(lambda x: x.strip(), usage.split())
        percent = percent.rstrip('%')
        return {
            'mountpoint': self.mountpoint,
            'size': long(size),
            'used': long(used),
            'free': long(free),
            'percent': int(percent)
        }

def load_mountpoints():
    """
    Update list of FreeBSD mountpoints based on /sbin/mount output
    """
    mountpoints = []

    try:
        output = check_output(['/sbin/mount'])
    except CalledProcessError:
        raise FileSystemError('Error running /sbin/mount')

    for l in [l for l in output.split('\n') if l.strip()!='']:
        if l[:4] == 'map ':
            continue

        m = RE_MOUNT.match(l)
        if not m:
            continue

        device = m.group(1)
        mountpoint = m.group(2)
        flags = map(lambda x: x.strip(), m.group(3).split(','))
        filesystem = flags[0]
        flags = flags[1:]

        entry = BSDMountPoint(device, mountpoint, filesystem)
        for f in flags:
            entry.flags.set(f,True)

        mountpoints.append(entry)

    return mountpoints
