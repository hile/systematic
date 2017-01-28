"""
Counters from vmstat for Darwin
"""

from collections import OrderedDict
from systematic.platform import SystemStatsParser, SystemStatsCounter, SystemStatsCounterGroup

VMSTAT_FIELD_MAP = {
    'Pages free':                   'pages_free',
    'Pages active':                 'pages_free',
    'Pages inactive':               'pages_inactive',
    'Pages speculative':            'pages_speculative',
    'Pages throttled':              'throttled',
    'Pages wired down':             'wired_down',
    'Pages purgeable':              'purgeable',
    '"Translation faults"':         'translation_faults',
    'Pages copy-on-write':          'copy_on_write',
    'Pages zero filled':            'zero_filled',
    'Pages reactivated':            'reactivated',
    'Pages purged':                 'purged',
    'File-backed pages':            'file_backed',
    'Anonymous pages':              'anonyous',
    'Pages stored in compressor':   'stored_in_compressor',
    'Pages occupied by compressor': 'occupied_by_compresspr',
    'Decompressions':               'decompressions',
    'Compressions':                 'compressions',
    'Pageins':                      'page_ins',
    'Pageouts':                     'page_outs',
    'Swapins':                      'swap_ins',
    'Swapouts':                     'swap_outs',
}


class DarwinVMStats(SystemStatsParser):
    """Darwin vm_stat counters

    Virtual memory counters from Mach kernel with vm_stat
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
        stdout, stderr = self.execute( ( 'vm_stat' ) )
        group = self.__get_or_add_counter_group__('mach_vm_stats')
        for line in stdout.splitlines()[1:]:
            key, value = [v.strip() for v in line.split(':', 1)]
            value = value.rstrip('.')
            group.add_counter(VMSTAT_FIELD_MAP[key], int(value))
        self.update_timestamp()


class DarwinDiskStats(SystemStatsParser):
    """Darwin iostat counters

    """
    name = 'iostat'

    def update(self):
        """Update iostat disk counters

        """
        self.counters = OrderedDict()
        stdout, stderr = self.execute( ( 'iostat', '-dn20', ) )
        disks = stdout.splitlines()[0].split()
        for line in stdout.splitlines()[2:]:
            data = line.split()
            for i, disk in enumerate(disks):
                group = self.__get_or_add_counter_group__(disk)
                group.add_counter('kb_per_transfer', float(data[i*3]))
                group.add_counter('transfers', int(data[i*3+1]))
                group.add_counter('megabytes', float(data[i*3+2]))
        self.update_timestamp()


class DarwinSystemStats(SystemStatsParser):
    """Darwin system stats parser

    """
    def __init__(self):
        super(DarwinSystemStats, self).__init__()
        self.vm_stats = DarwinVMStats()
        self.disk_stats = DarwinDiskStats()

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

