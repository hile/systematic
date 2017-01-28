"""
Basic MacOS system information

Uses system_profiler to get data
"""

import re
import json
import plistlib
import time

from systematic.platform import SystemInformationParser

RE_BOOTTIME = re.compile('^{ sec = (?P<seconds>\d+), usec = (?P<microseconds>\d+) } .*$')

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
        self.hardware_information = {}
        self.system_information = {}
        self.memory_information = { 'banks': [] }
        self.sysctl.get("kern")
        self.update()

    @property
    def hostname(self):
        return self.sysctl["kern.hostname"].value

    @property
    def operatingsystem(self):
        return self.sysctl["kern.ostype"].value

    @property
    def kernel(self):
        return self.sysctl["kern.osrelease"].value

    @property
    def uptime(self):
        m = RE_BOOTTIME.match(self.sysctl["kern.boottime"].value)
        return time.time() - float('{0}.{1}'.format(m.groupdict()['seconds'], m.groupdict()['microseconds']))

    @property
    def release(self):
        return self.system_information['os_version']

    @property
    def cpus(self):
        return self.hardware_information['number_processors']

    @property
    def total_memory(self):
        stdout, stderr = self.execute('sysctl hw.memsize')
        return int(stdout.splitlines()[0].split(':')[1].strip()) / 1024

    def parse_vendor_data(self):
        """Parse MacOS vendor data

        """
        self.hardware_information = {}
        self.system_information = {}
        self.memory_information = { 'banks': [] }

        try:
            stdout, stderr = self.execute( ('system_profiler', '-xml', 'SPHardwareDataType') )
            data = plistlib.readPlistFromString(stdout)
            data = data[0]['_items'][0]
            for key, value in data.items():
                self.hardware_information[key] = data[key]
        except ShellCommandParserError as e:
            pass

        try:
            stdout, stderr = self.execute( ('system_profiler', '-xml', 'SPMemoryDataType') )
            data = plistlib.readPlistFromString(stdout)
            data = data[0]['_items'][0]
            self.memory_information['memory_upgradeable'] = data['is_memory_upgradeable'] == 'Yes'
            for key in ( 'global_ecc_state', ):
                self.memory_information[key] = data[key]
            for bank in data['_items']:
                self.memory_information['banks'].append(dict(bank.items()))
        except ShellCommandParserError as e:
            pass

        try:
            stdout, stderr = self.execute( ('system_profiler', '-xml', 'SPSoftwareDataType') )
            data = plistlib.readPlistFromString(stdout)
            data = data[0]['_items'][0]
            for key in SYSTEM_INFO_KEYS:
                try:
                    self.system_information[key] = data[key]
                except:
                    self.system_information[key] = None
        except ShellCommandParserError as e:
            pass

    def update(self):
        """Update details

        """
        super(SystemInformation, self).update()
        self.parse_vendor_data()

    def to_json(self, verbose=False):
        data = super(SystemInformation, self).as_dict()
        if verbose:
            data['vendor'] = {
                'hardware': self.hardware_information,
                'system': self.system_information,
                'memory': self.memory_information,
            }
        return json.dumps(data, indent=2, cls=self.json_encoder)
