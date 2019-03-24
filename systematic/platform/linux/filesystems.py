"""
Implementation of linux filesystem mount point parsing
"""
from __future__ import unicode_literals

import os
import re

from builtins import int, str

from systematic.classes import MountPoint, FileSystemError
from systematic.shell import ShellCommandParser, ShellCommandParserError

PSEUDO_FILESYSTEMS = (
    'proc',
    'sysfs',
    'cgroup',
    'autofs',
    'hugetlbfs',
    'mqueue',
    'devpts',
    'devtmpfs',
    'tmpfs',
    'fusectl',
    'pstore',
    'configfs',
    'selinuxfs',
    'securityfs',
    'debugfs',
    'rpc_pipefs',
    'binfmt_misc',
    'nfsd',
    'fuse.vmware-vmblock',
)

DM_PREFIX = '/dev/mapper/'
MAPPER_PATH = '/dev/mapper'

UUID_PATH = '/dev/disk/by-uuid'
LABEL_PATH = '/dev/disk/by-label'

RE_MOUNT = re.compile(r'([^\s]*) on (.*) type ([^\s]+) \(([^\)]*)\)$')


class LinuxMountPoint(MountPoint):
    """
    One linux mountpoint based on /bin/mount output line
    Additional attributes:
    uuid        Filesystem uuid
    label       Filesystem label
    """
    def __init__(self, mountpoints, device, mountpoint, filesystem):
        super(LinuxMountPoint, self).__init__(mountpoints, device, mountpoint, filesystem)

        if self.device[:len(DM_PREFIX)] == DM_PREFIX:
            for name in os.listdir(MAPPER_PATH):
                dev = os.path.realpath(os.path.join(MAPPER_PATH, name))
                if name == os.path.basename(self.device):
                    self.device = dev
                    break

        self.uuid = None
        for uuid in os.listdir(UUID_PATH):
            dev = os.path.realpath(os.path.join(UUID_PATH, uuid))
            if dev == self.device:
                self.uuid = str(uuid)
                break

        self.label = None
        if os.path.isdir(LABEL_PATH):
            for label in os.listdir(LABEL_PATH):
                dev = os.path.realpath(os.path.join(LABEL_PATH, label))
                if dev == self.device:
                    self.label = str(label)
                    break

    @property
    def is_virtual(self):
        return self.filesystem in PSEUDO_FILESYSTEMS

    def update_usage(self, line=None):
        """
        Check usage percentage for this mountpoint.
        Returns dictionary with usage details.
        """
        if self.filesystem in PSEUDO_FILESYSTEMS:
            return {}

        if line is None:
            parser = ShellCommandParser()
            try:
                stdout, stderr = parser.execute('df', '-Pk', self.mountpoint)
            except ShellCommandParserError:
                raise FileSystemError('Error getting usage for {0}'.format(self.mountpoint))

            header, usage = stdout.split('\n', 1)
            try:
                usage = ' '.join(usage.split('\n'))
            except ValueError:
                pass

        else:
            usage = ' '.join(line.split('\n'))

        fs, size, used, free, percent, mp = [x.strip() for x in usage.split()]
        percent = percent.rstrip('%')

        self.usage = {
            'mountpoint': self.mountpoint,
            'size': int(size),
            'used': int(used),
            'free': int(free),
            'percent': int(percent),
        }


def load_mountpoints(self):
    """
    Update list of linux mountpoints based on /bin/mount output
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
        filesystem = str(m.group(3))
        flags = [str(x.strip()) for x in m.group(4).split(',')]

        entry = LinuxMountPoint(self, device, mountpoint, filesystem)
        if entry.is_virtual:
            continue

        for f in flags:
            entry.flags.set(f, True)

        mountpoints.append(entry)

    try:
        stdout, stderr = parser.execute('df' '-Pk')
    except ShellCommandParserError as e:
        raise FileSystemError('Error running mount: {0}'.format(e))

    for mountpoint in mountpoints:
        for line in stdout.splitlines():
            if line.split()[0] == mountpoint.device:
                mountpoint.update_usage(line)

    return mountpoints
