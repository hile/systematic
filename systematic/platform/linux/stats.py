"""
Counters from vmstat for linux
"""

from collections import OrderedDict

from systematic.platform import SystemStatsParser


VMSTAT_FIELD_MAP = {
    'process': {
        'r':    'runnable',
        'b':    'blocked',
    },
    'memory': {
        'swpd':     'swapped',
        'free':     'idle',
        'buff':     'buffers',
        'cache':    'caches',
        'inact':    'inactive',
        'active':   'active',
    },
    'swap': {
        'si':       'swapped_in',
        'so':       'swapped_out',
    },
    'io': {
        'bi':       'blocks_in',
        'bo':       'blocks_out',
    },
    'system': {
        'in':       'interrupts',
        'cs':       'context_switches',
    },
    'cpu': {
        'us':       'user',
        'sy':       'kernel',
        'id':       'idle',
        'wa':       'wait',
        'st':       'stolen',
    },
}

VMSTAT_VM_MODE_FIELDS = (
    'r',
    'b',
    'swpd',
    'free',
    'inact',
    'active',
    'si',
    'so',
    'bi',
    'bo',
    'in',
    'cs',
    'us',
    'sy',
    'id',
    'wa',
    'st',
)

VMSTAT_DISK_MODE_FIELDS = (
    'device',
    'read_total',
    'read_merged',
    'read_sectors',
    'read_ms',
    'write_total',
    'write_merged',
    'write_sectors',
    'write_ms',
    'io_cur',
    'io_sec',
)


class LinuxVMStats(SystemStatsParser):
    """Linux vmstat counters in vm mode

    """
    name = 'vmstat'

    def __find_counter_group__(self, field):
        """Find counter group and name for field

        """
        for group, details in VMSTAT_FIELD_MAP.items():
            if field in details:
                return group, details[field]
        raise KeyError('Unknown VM stats field key: {0}'.format(field))

    def update(self):
        """Update vmstat vm counters

        """
        self.counters = OrderedDict()
        stdout, stderr = self.execute(('vmstat', '-aw'))
        data = stdout.splitlines()[-1].split()
        for i, field in enumerate(VMSTAT_VM_MODE_FIELDS):
            group, name = self.__find_counter_group__(field)
            group = self.__get_or_add_counter_group__(group)
            group.add_counter(name, int(data[i]))
        self.update_timestamp()


class LinuxDiskStats(SystemStatsParser):
    """Linux vmstat counters in disk mode

    """
    name = 'diskstat'

    def update(self):
        """Update vmstat disk counters

        """
        self.counters = OrderedDict()
        stdout, stderr = self.execute(('vmstat', '-dw'))
        for line in stdout.splitlines()[2:]:
            data = line.split()
            group = self.__get_or_add_counter_group__(data[0])
            for i, field in enumerate(VMSTAT_DISK_MODE_FIELDS[1:]):
                group.add_counter(field, int(data[i+1]))
        self.update_timestamp()


class LinuxSystemStats(SystemStatsParser):
    """Linux system stats parser

    """
    def __init__(self):
        super(LinuxSystemStats, self).__init__()
        self.vm_stats = LinuxVMStats()
        self.disk_stats = LinuxDiskStats()

    def update(self):
        """Update all counters

        """
        self.vm_stats.update()
        self.disk_stats.update()

    def as_dict(self, verbose=False):
        """Return stats as JSON

        Returns combined stats for disks and vm as dict
        """
        return {
            'disk': self.disk_stats.as_dict(),
            'vm': self.vm_stats.as_dict(),
        }
