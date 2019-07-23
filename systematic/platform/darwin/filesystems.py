"""
Abstraction of filesystem mount points for OS X
"""

from __future__ import unicode_literals

import os
import re

from builtins import int, str
from mactypes import Alias
from subprocess import Popen, PIPE

from systematic.classes import MountPoint, FileSystemError
from systematic.platform.darwin.diskutil import DiskInfo
from systematic.shell import ShellCommandParser, ShellCommandParserError

RE_MOUNTPOINT = re.compile(r'([^\s]*) on (.*) \(([^\)]*)\)$')
RE_DF = re.compile(r'^([^\s]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)%\s+(.*)$')

PSEUDO_FILESYSTEMS = (
    'devfs',
)


class DarwinMountPoint(MountPoint):
    """
    One OS X mountpoint parsed from /sbin/mount output

    Extra attributes:
    hfspath     Returns OS X 'hfs path' or None
    """
    def __init__(self, mountpoints, mountpoint, device=None, filesystem=None):
        super(DarwinMountPoint, self).__init__(mountpoints, device, mountpoint, filesystem)

        try:
            self.hfspath = str(Alias(self.mountpoint).hfspath)
        except ValueError:
            self.hfspath = None

        self.update_diskinfo()

    @property
    def is_virtual(self):
        return self.filesystem in PSEUDO_FILESYSTEMS

    def update_usage(self, line=None):
        """
        Check usage percentage for this mountpoint.
        Returns dictionary with usage details.
        """

        if line is None:
            parser = ShellCommandParser()
            try:
                stdout, stderr = parser.execute('df', '-k', self.mountpoint)
            except ShellCommandParserError as e:
                raise FileSystemError('Error checking filesystem usage: {0}'.format(e))

            header, usage = stdout.split('\n', 1)

        else:
            usage = line

        m = RE_DF.match(usage)
        if not m:
            raise FileSystemError('Error matching df output line: {0}'.format(usage))

        self.usage = {
            'mountpoint': self.mountpoint,
            'size': int(m.group(2)),
            'used': int(m.group(3)),
            'free': int(m.group(4)),
            'percent': int(m.group(5))
        }

    @property
    def name(self):
        if 'VolumeName' in self.diskinfo:
            return self.diskinfo['VolumeName']
        return super(DarwinMountPoint, self).name

    @property
    def writable(self):
        if 'Writable' in self.diskinfo:
            return self.diskinfo['Writable']
        return False

    @property
    def bootable(self):
        if 'Bootable' in self.diskinfo:
            return self.diskinfo['Bootable']
        return False

    @property
    def internal(self):
        if 'Internal' in self.diskinfo:
            return self.diskinfo['Internal']
        return False

    @property
    def ejectable(self):
        if 'Ejectable' in self.diskinfo:
            return self.diskinfo['Ejectable']
        return True

    @property
    def removable(self):
        if 'Removable' in self.diskinfo:
            return self.diskinfo['Removable']
        return False

    @property
    def blocksize(self):
        if 'DeviceBlockSize' in self.diskinfo:
            return self.diskinfo['DeviceBlockSize']
        return 0

    def update_diskinfo(self):
        """Update DiskInfo object

        Only available if user has read access to raw device

        """
        self.diskinfo = DiskInfo(self.device)

    def as_dict(self, verbose=False):
        """Data as dict

        """
        data = super(DarwinMountPoint, self).as_dict(verbose)

        if verbose:
            # These flags only report sensible data as root
            if os.geteuid() == 0:
                data.update(
                    writable=self.writable,
                    internal=self.internal,
                    ejectable=self.ejectable,
                    removable=self.removable,
                    blocksize=self.blocksize,
                )

        return data

    def detach(self):
        """
        Detach mountpoint with diskutil unmount
        """
        cmd = ['diskutil', 'unmount', self.path]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise FileSystemError('Error detaching {}: {}'.format(
                self.path,
                stderr.rstrip(),
            ))

        self.mountpoints.update()
        return self.path


def load_mountpoints(self):
    """
    Update mount points from /sbin/mount output
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

        m = RE_MOUNTPOINT.match(l)
        if not m:
            continue

        device = str(m.group(1))
        mountpoint = str(m.group(2))
        flags = [str(x.strip()) for x in m.group(3).split(',')]
        filesystem = flags[0]
        flags = flags[1:]

        entry = DarwinMountPoint(self, mountpoint, device, filesystem)
        if entry.is_virtual:
            continue

        for f in flags:
            if f[:11] == 'mounted by ':
                entry.flags.set('owner', f[11:])
            else:
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
