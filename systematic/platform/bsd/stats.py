"""
Counters from vmstat for BSD
"""

from collections import OrderedDict
from systematic.platform import SystemStatsParser

VMSTAT_FIELD_MAP = {
    'process': {
        'r':    'run_queue',
        'b':    'blocked',
        'w':    'runnable_but_swapped',
    },
    'memory': {
        'avm':  'active_vm_pages',
        'fre':  'free_list_size',
    },
    'page': {
        'flt':  'page_faults',
        're':   'page_reclaims',
        'pi':   'paged_in',
        'po':   'paged_out',
        'fr':   'pages_freed_per_second',
        'sr':   'pages_scanned_per_second',
    },
    'faults': {
        'in':   'interrupts',
        'sy':   'systemcalls',
        'cs':   'context_switch_rate',
    },
    'cpu': {
        'us':   'user',
        'sy':   'system',
        'id':   'idle',
    }
}

# Fields from vmstat -Hn0 output
VMSTAT_FIELDS = (
    'r',
    'b',
    'w',
    'avm',
    'fre',
    'flt',
    're',
    'pi',
    'po',
    'fr',
    'sr',
    'in',
    'sy',
    'cs',
    'us',
    'sy',
    'id',
)


class BSDVMStats(SystemStatsParser):
    """BSD vmstat counters

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
        stdout, stderr = self.execute(('vmstat', '-Hn0'))
        data = stdout.splitlines()[-1].split()
        for i, field in enumerate(VMSTAT_FIELDS):
            group, name = self.__find_counter_group__(field)
            group = self.__get_or_add_counter_group__(group)
            group.add_counter(name, int(data[i]))
        self.update_timestamp()


class BSDDiskStats(SystemStatsParser):
    """BSD iostat counters

    """
    name = 'iostat'

    def update(self):
        """Update iostat disk counters

        """
        self.counters = OrderedDict()
        stdout, stderr = self.execute(('iostat', '-dn20'))
        disks = stdout.splitlines()[0].split()
        for line in stdout.splitlines()[2:]:
            data = line.split()
            for i, disk in enumerate(disks):
                group = self.__get_or_add_counter_group__(disk)
                group.add_counter('kb_per_transfer', float(data[i*3]))
                group.add_counter('transfers', int(data[i*3+1]))
                group.add_counter('megabytes', float(data[i*3+2]))
        self.update_timestamp()


class BSDSystemStats(SystemStatsParser):
    """BSD system stats parser

    """
    def __init__(self):
        super(BSDSystemStats, self).__init__()
        self.vm_stats = BSDVMStats()
        self.disk_stats = BSDDiskStats()

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
