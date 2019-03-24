"""
Platform specific modules
"""

import json
import re
import sys
import time

from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from systematic.shell import ShellCommandParser

if sys.platform[:5] == 'linux':
    SYSCTL_SEPARATOR = '='
else:
    SYSCTL_SEPARATOR = ':'

RE_UPTIME_PATTERNS = (
    re.compile(
        r'^\s*(?P<time>[^\s]+)\s+up (?P<uptime>.*),\s+(?P<users>\d+) user,' +
        r'\s+load average: (?P<load_avg_1>[\d.]+), (?P<load_avg_5>[\d.]+), (?P<load_avg_15>[\d.]+)$'
    ),
    re.compile(
        r'^\s*(?P<time>[^\s]+)\s+up (?P<uptime>.*),\s+(?P<users>\d+) users,' +
        r'\s+load average: (?P<load_avg_1>[\d.]+), (?P<load_avg_5>[\d.]+), (?P<load_avg_15>[\d.]+)$'
    ),
    re.compile(
        r'^\s*(?P<time>[^\s]+)\s+up (?P<uptime>.*), (?P<users>\d+) users,' +
        r' load averages: (?P<load_avg_1>[\d.]+), (?P<load_avg_5>[\d.]+), (?P<load_avg_15>[\d.]+)$'
    ),
    re.compile(
        r'^\s*(?P<time>[^\s]+)\s+up (?P<uptime>.*), (?P<users>\d+) users,' +
        r'load averages: (?P<load_avg_1>[\d.]+) (?P<load_avg_5>[\d.]+) (?P<load_avg_15>[\d.]+)$'
    ),
)


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            encoded_object = list(obj.timetuple())[0:6]
        elif isinstance(obj, Decimal):
            encoded_object = float(obj)
        elif isinstance(obj, SystemStatsCounter):
            encoded_object = obj.value
        else:
            encoded_object = json.JSONEncoder.default(self, obj)
        return encoded_object


class SysCtl(object):
    """Sysctl variable

    Variable defined from SysCtlParser
    """
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return '{}'.format(self.value)


class SysCtlParser(dict, ShellCommandParser):
    """Caching parser for sysctl keys

    Read data with sysctl command, cache responses
    """
    def __getitem__(self, item, ):
        if item not in self:
            self.get(item)
        return super(SysCtlParser, self).__getitem__(item)

    def get(self, key):
        """Get current value

        """
        stdout, stderr = self.execute('sysctl', key)

        sysctl = None
        for line in stdout.splitlines():
            try:
                key, value = line.split(SYSCTL_SEPARATOR, 1)
                key = key.strip()
                value = value.strip()
                sysctl = SysCtl(key, value)
                self[key] = sysctl
            except ValueError:
                if sysctl is not None:
                    sysctl.value += line


class SystemInformationParser(ShellCommandParser):
    """Common system information

    """
    json_encoder = JSONEncoder

    def __init__(self, *args, **kwargs):
        super(ShellCommandParser, self).__init__(*args, **kwargs)
        self.sysctl = SysCtlParser()

    @property
    def kernel(self):
        stdout, stderr = self.execute('uname', '-r')
        return stdout.splitlines()[0]

    @property
    def hostname(self):
        stdout, stderr = self.execute('uname', '-n')
        return stdout.strip()

    @property
    def uptime(self):
        return 0

    @property
    def cpus(self):
        return 0

    @property
    def total_memory(self):
        return 0

    @property
    def operatingsystem(self):
        """Return OS system type

        Return OS system type as reported by uname -s
        """
        stdout, stderr = self.execute('uname', '-s')
        return stdout.splitlines()[0]

    @property
    def release(self):
        """
        Return OS system release

        Return OS system type as reported by uname -r
        """
        stdout, stderr = self.execute('uname', '-r')
        return stdout.splitlines()[0]

    def update(self):
        """Parse common details

        """
        return

    def as_dict(self, verbose=False):
        return {
            'hostname': self.hostname,
            'operatingsystem': self.operatingsystem,
            'kernel': self.kernel,
            'release': self.release,
            'uptime': self.uptime,
            'cpus': self.cpus,
            'memory': self.total_memory,
        }

    def to_json(self, verbose=False):
        data = self.as_dict(verbose=verbose)
        return json.dumps(data, indent=2, cls=self.json_encoder)


class SystemStatsCounter(object):
    """Single counter key/value pair

    """
    def __init__(self, key, value):
        self.key = key
        self.value = value


class SystemStatsCounterGroup(OrderedDict):
    """Group of counters

    """
    def __init__(self, name):
        super(SystemStatsCounterGroup, self).__init__()
        self.name = name

    def add_counter(self, key, value):
        """Add counter

        """
        self[key] = SystemStatsCounter(key, value)


class SystemStatsParser(ShellCommandParser):
    """Common parser for vmstat classes

    Common code for platform dependent vmstat parsers
    """
    json_encoder = JSONEncoder
    name = 'unknown'

    def __init__(self):
        super(SystemStatsParser, self).__init__()
        self.__updated__ = None
        self.counters = OrderedDict()

    def __get_or_add_counter_group__(self, group):
        """Get or add new counter group

        """
        if group not in self.counters:
            self.counters[group] = SystemStatsCounterGroup(group)
        return self.counters[group]

    def update_timestamp(self):
        """Update timestamp

        Update self.__updated__
        """
        self.__updated__ = float(time.time())
        return self.__updated__

    def as_dict(self, verbose=False):
        """Return counters as dictionary

        """
        return {
            'timestamp': self.__updated__,
            'counters': self.counters,
        }

    def to_json(self, verbose=False):
        data = self.as_dict(verbose=verbose)
        return json.dumps(data, indent=2, cls=self.json_encoder)
