"""
ZFS volume status
"""

from collections import OrderedDict
from datetime import datetime
from systematic.shell import ShellCommandParser, ShellCommandParserError
from systematic.filesystems import FilesystemError

# Order of fields in zfs list -Hp output
ZFS_LIST_FIELDS = (
    'name',
    'used',
    'available',
    'references',
    'mountpoint',
)

# Known ZFS properties
ZFS_PROPERTIES = (
    'available',
    'clones',
    'compressratio',
    'creation',
    'defer_destroy',
    'logicalreferenced',
    'logicalused',
    'mounted',
    'origin',
    'receive_resume_token',
    'refcompressratio',
    'referenced',
    'type',
    'used',
    'usedbychildren',
    'usedbydataset',
    'usedbyrefreservation',
    'usedbysnapshots',
    'userrefs',
    'written',
    'aclinherit',
    'aclmode',
    'atime',
    'canmount',
    'casesensitivity',
    'checksum',
    'compression',
    'copies',
    'dedup',
    'devices',
    'exec',
    'filesystem_count',
    'filesystem_limit',
    'jailed',
    'logbias',
    'mlslabel',
    'mountpoint',
    'nbmand',
    'normalization',
    'primarycache',
    'quota',
    'readonly',
    'recordsize',
    'redundant_metadata',
    'refquota',
    'refreservation',
    'reservation',
    'secondarycache',
    'setuid',
    'sharenfs',
    'sharesmb',
    'snapdir',
    'snapshot_count',
    'snapshot_limit',
    'sync',
    'utf8only',
    'version',
    'volblocksize',
    'volmode',
    'volsize',
    'vscan',
    'xattr',
)

ZFS_BOOLEAN_PROPERTIES = (
    'defer_destroy',
    'mounted',
    'atime',
    'devices',
    'exec',
    'jailed',
    'nbmand',
    'readonly',
    'setuid',
    'utf8only',
    'vscan',
    'xattr',
)

# Note: some of these may return 'none' string which is parsed to None
ZFS_INTEGER_PROPERTIES = (
    'available',
    'creation',
    'logicalused',
    'referenced',
    'used',
    'usedbychildren',
    'usedbydataset',
    'usedbysnapshots',
    'written',
    'filesystem_count',
    'copies',
    'refquota',
    'refreservation',
    'reservation',
    'snapshot_count',
    'snapshot_limit',
)


class ZFS(ShellCommandParser):
    """ZFS volumes

    If filesystem is zvol, self.fstype = zvol and self.mountpoint = None
    """
    def __init__(self, client, name, used, available, references, mountpoint):
        super(ZFS, self).__init__()
        self.client = client
        self.name = name.decode('utf-8')
        self.used = int(used)
        self.available = available != '-' and int(available) or None
        self.references = int(references)

        if mountpoint == '-':
            self.fstype = u'zvol'
            self.mountpoint = None
        else:
            self.fstype = u'zfs'
            self.mountpoint = mountpoint is not None and mountpoint or None


    def __repr__(self):
        return '{0} {1} {2} GB'.format(
            self.fstype,
            self.name,
            self.used_gb,
        )

    def __getattr__(self, attr):
        """Get properties or attr

        """
        if attr in ZFS_PROPERTIES:
            return self.get_property(attr)
        raise AttributeError

    @property
    def used_gb(self):
        """Used size in GB

        """
        return u'{0:d}'.format(self.used / 1024 / 1024 / 1024)

    @property
    def available_gb(self):
        return u'{0:d}'.format(self.available / 1024 / 1024 / 1024)

    @property
    def created(self):
        """Return created datetime

        """
        return datetime.utcfromtimestamp(self.get_property('creation'))

    @property
    def zpool(self):
        """Return zpool name

        """
        return self.name.split('/')[0]

    @property
    def properties(self):
        """Get values for all properties

        Please note this is SLOW - it runs 'zfs get' for all known keys separately!
        """
        properties = OrderedDict()
        for name in ZFS_PROPERTIES:
            try:
                properties[name] = self.get_property(name)
            except FilesystemError:
                properties[name] = None
        return properties

    def get_property(self, name):
        """Get property value

        """
        if name not in ZFS_PROPERTIES:
            raise FilesystemError('Unknown property: {0}'.format(name))

        try:
            stdout, stderr = self.execute(('zfs', 'get', '-Hp', name, self.name))
        except ShellCommandParserError as e:
            raise FilesystemError('zfs {0}: error getting property {1}: {2}'.format(self.name, name, e))

        try:
            fields = stdout.splitlines()[0].split('\t')
        except Exception as e:
            raise FilesystemError('Error parsing {0}: {1}'.format(stdout, e))

        if fields[0] != self.name or fields[1] != name:
            raise FilesystemError('unexpected output. {0}'.format(stdout))

        value = fields[2]
        if name in ZFS_INTEGER_PROPERTIES:
            if value in ( 'none', '-', ):
                return None
            return int(value)
        elif name in ZFS_BOOLEAN_PROPERTIES:
            return value == 'yes'
        elif value == '-':
            value = None
        return value


class ZFSVolume(ZFS):
    """ZFS volume

    If filesystem is zvol, self.fstype = zvol and self.mountpoint = None
    """
    def __init__(self, client, name, used, available, references, mountpoint):
        super(ZFSVolume, self).__init__(client, name, used, available, references, mountpoint)

    def as_dict(self, verbose=False):
        """Volume details as dict

        """
        data = {
            'name': self.name,
            'fstype': self.fstype,
            'mountpoint': self.mountpoint,
            'available': self.available,
            'used': self.used,
            'references': self.references,
        }
        if verbose:
            data['properties'] = self.properties
        return data


class ZFSSnapshot(ZFS):
    """ZFS volume snapshot

    """
    def __init__(self, client, name, used, available, references, mountpoint):
        super(ZFSSnapshot, self).__init__(client, name, used, available, references, mountpoint)
        self.fstype = 'snapshot'
        self.mountpoint = mountpoint != '-' and mountpoint or None

    @property
    def volume(self):
        return self.name.split('@')[0]

    @property
    def snapshot(self):
        return self.name.split('@')[1]

    def as_dict(self, verbose=False):
        """Snapshot details as dict

        """
        data = {
            'volume': self.volume,
            'snapshot': self.snapshot,
            'used': self.used,
            'references': self.references,
        }
        if verbose:
            data['properties'] = self.properties
        return data


class ZfsClient(ShellCommandParser):
    """ZFS volumes

    Detect existing zfs volumes. Loads the volumes to ZfsClient.volumes as ZFS objects
    """
    def __init__(self, *args, **kwargs):
        super(ZfsClient, self).__init__(*args, **kwargs)
        self.volumes = []
        self.snapshots = []

    def load_volumes(self):
        """Update ZFS volumes

        """
        self.volumes = []
        cmd = ( 'zfs', 'list', '-Hp' )
        try:
            stdout, stderr = self.execute(cmd)
        except ShellCommandParserError as e:
            raise FilesystemError('Error listing zfs volumes: {0}'.format(e))

        for line in stdout.splitlines():
            self.volumes.append(ZFSVolume(self, **dict((ZFS_LIST_FIELDS[i], v) for i,v in enumerate(line.split('\t')))))

    def load_snapshots(self):
        """Update ZFS snapshots

        """
        self.snapshots = []
        cmd = ( 'zfs', 'list', '-Hpt', 'snapshot' )
        try:
            stdout, stderr = self.execute(cmd)
        except ShellCommandParserError as e:
            raise FilesystemError('Error listing zfs snapshots: {0}'.format(e))

        for line in stdout.splitlines():
            self.snapshots.append(ZFSSnapshot(self, **dict((ZFS_LIST_FIELDS[i], v) for i,v in enumerate(line.split('\t')))))
