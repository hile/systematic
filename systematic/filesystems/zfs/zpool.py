"""
ZFS zpool status
"""

from systematic.shell import ShellCommandParser, ShellCommandParserError
from systematic.filesystems import FilesystemError

# Order of fields in zpool list -Hp output
ZPOOL_LIST_FIELDS = (
    'name',
    'size',
    'used',
    'available',
    'expandsize',
    'fragmentation',
    'capacity',
    'deduplication',
    'health',
    'altroot',
)

# Known zpool properties
ZPOOL_PROPERTIES = (
    'allocated',
    'capacity',
    'dedupratio',
    'expandsize',
    'fragmentation',
    'free',
    'freeing',
    'guid',
    'health',
    'leaked',
    'size',
    'altroot',
    'autoexpand',
    'autoreplace',
    'bootfs',
    'cachefile',
    'comment',
    'dedupditto',
    'delegation',
    'failmode',
    'listsnapshots',
    'readonly',
    'version',
)

# Known zpool features (as in FreeBSD 11.0)
ZPOOL_FEATURES = (
    'async_destroy',
    'empty_bpobj',
    'filesystem_limits',
    'lz4_compress',
    'multi_vdev_crash_dump',
    'spacemap_histogram',
    'extensible_dataset',
    'bookmarks',
    'enabled_txg',
    'hole_birth',
    'embedded_data',
    'large_blocks',
    'sha512',
    'skein',
)

# Multiplier unit conversions
UNIT_MULTIPLIERS = {
    'B':    1,
    'K':    2**10,
    'M':    2**20,
    'G':    2**30,
    'T':    2**40,
    'P':    2**50,
    'E':    2**60,
    'Z':    2**70,
}


class ZPoolIostatCounters(dict):
    """Zpool device iostat counters

    """
    def __init__(self, parent, name, alloc, free, read_ops, write_ops, read_bw, write_bw):
        self['name'] = name.strip()
        self['allocated'] = alloc != '-' and self.__parse_counter_value__(alloc) or None
        self['free'] = free != '-' and self.__parse_counter_value__(free) or None
        self['operations'] = {
            'read': self.__parse_counter_value__(read_ops),
            'write': self.__parse_counter_value__(write_ops),
        }
        self['bandwidth'] = {
            'read': self.__parse_counter_value__(read_bw),
            'write': self.__parse_counter_value__(write_bw),
        }

    def __parse_counter_value__(self, value):
        """Parse counter value to int

        """
        try:
            return int(value)
        except ValueError:
            try:
                multiplier = UNIT_MULTIPLIERS[value[-1]]
                return int(float(value[:-1]) * multiplier)
            except ValueError:
                return value

    def add_device(self, device):
        """Add subdevice to counters

        """
        if 'devices' not in self:
            self['devices'] = []
        self['devices'].append(device)


class ZPoolIostat(ShellCommandParser):
    """Zpool iostat

    Iostat for a zpool
    """
    def __init__(self, zpool):
        self.zpool = zpool
        self.counters = None
        self.update()

    def update(self):
        """Update iostat counters

        """
        def prefixlen(line):
            count = 0
            for c in line:
                if c == ' ':
                    count += 1
                else:
                    break
            return count

        self.counters = None
        prefix = None
        parent = None
        previous = None

        stdout, stderr = self.execute(('zpool', 'iostat', '-v', self.zpool))
        for line in stdout.splitlines()[2:]:

            if line.startswith('-'):
                if parent is not None:
                    break
                continue

            if line.strip() == '':
                break

            device, alloc, free, read_ops, write_ops, read_bw, write_bw = line.split()
            counters = ZPoolIostatCounters(
                parent,
                device,
                alloc,
                free,
                read_ops,
                write_ops,
                read_bw,
                write_bw
            )
            lineprefix = prefixlen(line)

            if parent is None:
                self.counters = counters
                parent = counters
                prefix = 0

            else:
                if prefix is not None and prefix != lineprefix:
                    prefix = lineprefix
                    parent = previous
                parent.add_device(counters)

            previous = counters


class ZPool(ShellCommandParser):
    """ZFS zpool

    ZFS pool linked to ZFSPools.zpools
    """
    def __init__(self, name, size, used, available, expandsize, fragmentation,
                 capacity, deduplication, health, altroot):
        super(ZPool, self).__init__()
        self.iostat = ZPoolIostat(name)
        self.name = name
        self.size = int(size)
        self.used = int(used)
        self.available = int(available)
        self.expandsize = expandsize
        self.fragmentation = int(fragmentation.replace('%', ''))
        self.capacity = int(capacity)
        self.deduplication = float(deduplication.replace('x', ''))
        self.health = health
        self.altroot = altroot

    def __repr__(self):
        return '{0} {1:8} {2}/{3} GB'.format(
            self.name,
            self.health,
            self.used_gb,
            self.size_gb
        )

    @property
    def used_gb(self):
        """Used size in GB

        """
        return u'{0:d}'.format(int(self.used / 1024 / 1024 / 1024))

    @property
    def available_gb(self):
        """Available size in GB

        """
        return u'{0:d}'.format(int(self.available / 1024 / 1024 / 1024))

    @property
    def size_gb(self):
        """Total size in GB

        """
        return u'{0:d}'.format(int(self.size / 1024 / 1024 / 1024))

    @property
    def features(self):
        """All zpool features

        """
        return dict((key, self.get_feature(key)) for key in ZPOOL_FEATURES)

    @property
    def properties(self):
        """All zpool features

        """
        return dict((key, self.get_property(key)) for key in ZPOOL_PROPERTIES)

    def get_property(self, name):
        """Get property value

        """
        if name not in ZPOOL_PROPERTIES:
            raise FilesystemError('Unknown property: {0}'.format(name))

        try:
            stdout, stderr = self.execute(('zpool', 'get', '-H', name, self.name))
        except ShellCommandParserError as e:
            raise FilesystemError('zpool {0}: error getting property {1}: {2}'.format(self.name, name, e))

        try:
            fields = stdout.splitlines()[0].split('\t')
        except Exception as e:
            raise FilesystemError('Error parsing {0}: {1}'.format(stdout, e))

        if fields[0] != self.name or fields[1] != name:
            raise FilesystemError('unexpected output. {0}'.format(stdout))

        value = fields[2]
        if value == '-':
            value = None
        return value

    def get_feature(self, feature):
        """Get feature value

        """
        if feature not in ZPOOL_FEATURES:
            raise FilesystemError('Unknown feature: {0}'.format(feature))

        name = 'feature@{0}'.format(feature)
        try:
            stdout, stderr = self.execute(('zpool', 'get', '-H', name, self.name))
        except ShellCommandParserError as e:
            raise FilesystemError('zpool {0}: error getting feature {1}: {2}'.format(self.name, feature, e))

        try:
            fields = stdout.splitlines()[0].split('\t')
        except Exception as e:
            raise FilesystemError('Error parsing {0}: {1}'.format(stdout, e))

        if fields[0] != self.name or fields[1] != name:
            raise FilesystemError('unexpected output. {0}'.format(stdout))

        return fields[2]

    def as_dict(self, verbose=False):
        """Return zfs details

        Return details as dict for JSON serialization
        """
        data = {
            'name': self.name,
            'available': self.available,
            'used': self.used, 'capacity': self.capacity,
            'size': self.size,
            'health': self.health,
            'deduplication': self.deduplication,
            'expandsize': self.expandsize,
            'fragmentation': self.fragmentation,
            'altroot': self.altroot,
            'iostat': self.iostat.counters,
        }
        if verbose:
            data['features'] = self.features
            data['properties'] = self.properties
        return data


class ZPoolClient(ShellCommandParser):
    """ZFS zpools

    Detect existing zfs zpools. Loads the zpools to ZFSPools.pools as Zpool objects
    """
    def __init__(self, *args, **kwargs):
        super(ZPoolClient, self).__init__(*args, **kwargs)
        self.zpools = []

    def load_zpools(self):
        """Update ZFS pools

        """
        self.zpools = []
        cmd = ('zpool', 'list', '-Hp')
        try:
            stdout, stderr = self.execute(cmd)
        except ShellCommandParserError as e:
            raise FilesystemError('Error listing zfs pools: {0}'.format(e))

        for line in stdout.splitlines():
            self.zpools.append(ZPool(**dict(
                (ZPOOL_LIST_FIELDS[i], v)
                for i, v in enumerate(line.split('\t'))
            )))
