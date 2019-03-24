"""
Implementation of FreeBSD filesystem mount point parsing
"""

from __future__ import unicode_literals

import re

from builtins import int, str

from systematic.classes import MountPoint, FileSystemError
from systematic.shell import ShellCommandParser, ShellCommandParserError

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
    def __init__(self, mountpoints, device, mountpoint, filesystem):
        super(BSDMountPoint, self).__init__(mountpoints, device, mountpoint, filesystem)

    @property
    def is_virtual(self):
        return self.filesystem in PSEUDO_FILESYSTEMS

    def update_usage(self, line=None):
        """Update usage percentage for this mountpoint

        If line is provided, it's expected to be output from df -k. Otherwise df -k is called explicitly.

        Returns dictionary with usage details.
        """
        if self.filesystem in PSEUDO_FILESYSTEMS:
            return {}

        if line is None:
            parser = ShellCommandParser()
            try:
                stdout, stderr = parser.execute(('df', '-k', self.mountpoint))
            except ShellCommandParserError:
                raise FileSystemError('Error getting usage for {0}'.format(self.mountpoint))

            header, usage = stdout.split('\n', 1)
            try:
                usage = ' '.join(usage.split('\n'))
            except ValueError:
                pass
        else:
            usage = ' '.join(line.split('\n'))

        fs, size, used, free, percent, mp = [str(x.strip()) for x in usage.split()]
        percent = percent.rstrip('%')
        self.usage = {
            'mountpoint': self.mountpoint,
            'size': int(size),
            'used': int(used),
            'free': int(free),
            'percent': int(percent)
        }


def load_mountpoints(self):
    """
    Update list of FreeBSD mountpoints based on /sbin/mount output
    """
    mountpoints = []

    parser = ShellCommandParser()
    try:
        stdout, stderr = parser.execute('mount')
    except ShellCommandParserError as e:
        raise FileSystemError('Error running mount: {0}'.format(e))

    for l in [l for l in stdout.split('\n') if l.strip() != '']:
        if l[:4] == 'map ':
            continue

        m = RE_MOUNT.match(l)
        if not m:
            continue

        device = str(m.group(1))
        mountpoint = str(m.group(2))
        flags = [str(x.strip()) for x in m.group(3).split(',')]
        filesystem = flags[0]
        flags = flags[1:]

        entry = BSDMountPoint(self, device, mountpoint, filesystem)
        if entry.is_virtual:
            continue

        for f in flags:
            entry.flags.set(f, True)

        mountpoints.append(entry)

    try:
        stdout, stderr = parser.execute('df', '-k')
    except ShellCommandParserError as e:
        raise FileSystemError('Error running mount: {0}'.format(e))

    for mountpoint in mountpoints:
        for line in stdout.splitlines():
            if line.split()[0] == mountpoint.device:
                mountpoint.update_usage(line)

    return mountpoints
