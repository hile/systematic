"""
Basic MacOS system information

Uses system_profiler to get data
"""

import re
import json
import plistlib
import time

from io import BytesIO
from systematic.platform import SystemInformationParser
from systematic.shell import ShellCommandParserError

RE_BOOTTIME = re.compile(r'^{ sec = (?P<seconds>\d+), usec = (?P<microseconds>\d+) } .*$')

SYSTEM_INFO_KEYS = (
    'os_version',
    'kernel_version',
    'boot_volume',
    'local_host_name',
    'uptime',
    'system_integrity',
    'secure_vm',
    'boot_mode',
)


class SystemInformation(SystemInformationParser):
    """Basic MacOS system information

    """

    def __init__(self):
        super(SystemInformation, self).__init__()
        self.sysctl.get('kern')
        self.platform_data = None
        self.update()

    @property
    def hostname(self):
        return self.sysctl['kern.hostname'].value

    @property
    def operatingsystem(self):
        return self.sysctl['kern.ostype'].value

    @property
    def kernel(self):
        return self.sysctl['kern.osrelease'].value

    @property
    def uptime(self):
        m = RE_BOOTTIME.match(self.sysctl['kern.boottime'].value)
        return time.time() - float('{0}.{1}'.format(m.groupdict()['seconds'], m.groupdict()['microseconds']))

    @property
    def release(self):
        return self.system_information['os_version']

    @property
    def cpus(self):
        return self.hardware_information['number_processors']

    @property
    def total_memory(self):
        stdout, stderr = self.execute('sysctl', 'hw.memsize')
        return int(stdout.splitlines()[0].split(':')[1].strip()) / 1024

    @property
    def hardware_information(self):
        if not self.platform_data:
            self.__parse_vendor_data__()
        return self.platform_data['hardware_information']

    @property
    def system_information(self):
        if not self.platform_data:
            self.__parse_vendor_data__()
        return self.platform_data['system_information']

    @property
    def memory_information(self):
        if not self.platform_data:
            self.__parse_vendor_data__()
        return self.platform_data['memory_information']

    def __parse_vendor_data__(self):
        """Parse MacOS vendor data

        """
        self.platform_data = {
            'hardware_information': {},
            'system_information': {},
            'memory_information': {'banks': []}
        }

        try:
            stdout, stderr = self.execute('system_profiler', '-xml', 'SPHardwareDataType')
            data = plistlib.readPlist(BytesIO(bytes(stdout, 'utf-8')))
            data = data[0]['_items'][0]
            for key in data:
                self.platform_data['hardware_information'][key] = data[key]
        except ShellCommandParserError:
            pass

        try:
            stdout, stderr = self.execute('system_profiler', '-xml', 'SPMemoryDataType')
            data = plistlib.readPlist(BytesIO(bytes(stdout, 'utf-8')))
            data = data[0]['_items'][0]
            self.memory_information['memory_upgradeable'] = data['is_memory_upgradeable'] == 'Yes'
            for key in ('global_ecc_state',):
                self.platform_data['memory_information'][key] = data[key]
            for bank in data['_items']:
                self.memory_information['banks'].append(dict(bank.items()))
        except ShellCommandParserError:
            pass

        try:
            stdout, stderr = self.execute('system_profiler', '-xml', 'SPSoftwareDataType')
            data = plistlib.readPlist(BytesIO(bytes(stdout, 'utf-8')))
            data = data[0]['_items'][0]
            for key in SYSTEM_INFO_KEYS:
                try:
                    self.platform_data['system_information'][key] = data[key]
                except KeyError:
                    self.platform_data['system_information'][key] = None
        except ShellCommandParserError:
            pass

    def to_json(self, verbose=False):
        data = super(SystemInformation, self).as_dict()
        if verbose:
            data['vendor'] = {
                'hardware': self.hardware_information,
                'system': self.system_information,
                'memory': self.memory_information,
            }
        return json.dumps(data, indent=2, cls=self.json_encoder)
