"""
Basic BSD system information

"""

import re
import json
import time

RE_BOOTTIME = re.compile('^{ sec = (?P<seconds>\d+), usec = (?P<microseconds>\d+) } .*$')

from systematic.platform import SystemInformationParser


class SystemInformation(SystemInformationParser):
    """Basic BSD system information

    """

    def __init__(self):
        super(SystemInformation, self).__init__()
        self.update()

    @property
    def cpus(self):
        stdout, stderr = self.execute('sysctl hw.ncpu')
        return int(stdout.splitlines()[0].split(':')[1].strip())

    @property
    def uptime(self):
        m = RE_BOOTTIME.match(self.sysctl["kern.boottime"].value)
        return time.time() - float('{0}.{1}'.format(m.groupdict()['seconds'], m.groupdict()['microseconds']))

    @property
    def total_memory(self):
        stdout, stderr = self.execute('sysctl hw.physmem')
        return int(stdout.splitlines()[0].split(':')[1].strip()) / 1024

    @property
    def total_memory(self):
        stdout, stderr = self.execute('sysctl hw.physmem')
        return int(stdout.splitlines()[0].split(':')[1].strip()) / 1024

    @property
    def release(self):
        stdout, stderr = self.execute('freebsd-version -u')
        return stdout.splitlines()[0]

    def update(self):
        """Update details

        """
        super(SystemInformation, self).update()

        self.parse_dmi()
