"""
Wrapper for OS/X diskutil command for python
"""

import os
import plistlib
import StringIO
from xml.parsers.expat import ExpatError
from subprocess import Popen, PIPE

INFO_FIELD_MAP = {
    'DeviceNode':       {'name': 'Device', 'value': lambda x: str(x)},
    'FilesystemName':   {'name': 'Filesystem', 'value': lambda x: str(x)},
    'UsedSpace':        {'name': 'Used', 'value': lambda x: x/1024},
    'UsedPercent':      {'name': 'Percent', 'value': lambda x: x/1024},
    'FreeSpace':        {'name': 'Free', 'value': lambda x: x/1024},
    'TotalSize':        {'name': 'Sizd', 'value': lambda x: x/1024},
    'VolumeName':       {'name': 'Volume Name', 'value': lambda x: str(x)},
    'VolumeUUID':       {'name': 'UUID', 'value': lambda x: str(x)},
}
INFO_FIELD_ORDER = [
    'DeviceNode',
    'VolumeName',
    'FilesystemName',
    'VolumeUUID',
    'UsedSpace',
    'FreeSpace',
    'TotalSize'
]

class DiskUtilError(Exception):
    pass

class DiskInfo(dict):
    def __init__(self, device):
        if not os.access(device, os.R_OK):
            raise DiskUtilError('Device not readable: %s' % device)

        cmd = ['diskutil', 'info', '-plist', device]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = p.communicate()
        try:
            plist = StringIO.StringIO(stdout)
            self.update(plistlib.readPlist(plist))
        except ExpatError, emsg:
            raise DiskUtilError('Error parsing plist: %s' % stdout)

        if self.has_key('TotalSize') and self.has_key('FreeSpace'):
            self['UsedSpace'] = self.TotalSize - self.FreeSpace
            self['UsedPercent'] = int(round(1-(float(self.FreeSpace) / float(self.TotalSize))))

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError

    def keys(self):
        """
        Return keys as sorted list
        """
        return sorted(dict.keys(self))

    def items(self):
        """
        Return (key, value) sorted by key
        """
        return [(k, self[k]) for k in self.keys()]

    def values(self):
        """
        Return values sorted by key
        """
        return [self[k] for k in self.keys()]
