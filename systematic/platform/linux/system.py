"""
Basic linux system information

"""

import json
import os

from systematic.platform import SystemInformationParser

CPUINFO_BOOLEAN_FIELDS = (
    'fpu',
    'fpu_exception',
    'wp',
)
CPUINFO_FLOAT_FIELDS = (
    'cpu MHz',
    'bogomips',
)
CPUINFO_INTEGER_FIELDS = (
    'cpu family',
    'model',
    'model name',
    'stepping',
    'microcode',
    'cpu MHz',
    'cache size',
    'physical id',
    'siblings',
    'core id',
    'cpu cores',
    'apicid',
    'initial apicid',
    'cpuid level',
    'clflush size',
    'cache_alignment',
)
CPUINFO_LIST_FIELDS = (
    'flags',
)


class OSInfo(dict):
    """OS info

    Based on /etc/os-release
    """
    pass


class CPUInfo(dict):
    """CPU info

    Processor from /proc/cpuinfo
    """
    def __init__(self, index):
        self.index = index

    def __repr__(self):
        return 'CPU {0}'.format(self.index)

    def __setitem__(self, key, value):
        if key in CPUINFO_BOOLEAN_FIELDS:
            value = value in ( 'yes', 'on', )
        elif key in CPUINFO_INTEGER_FIELDS:
            value = int(value)
        elif key in CPUINFO_FLOAT_FIELDS:
            value = float(value)
        elif key in CPUINFO_LIST_FIELDS:
            value = value.split()
        super(CPUInfo, self).__setitem__(key, value)


class MemInfo(dict):
    """Memory info

    Memory details based on /proc/meminfo
    """

    def __setitem__(self, key, value):
        if value[-3:] == ' kB':
            value = value[:-3]
        value = int(value)
        super(MemInfo, self).__setitem__(key, value)


class SystemInformation(SystemInformationParser):
    """Basic linux system information

    """

    def __init__(self):
        super(SystemInformation, self).__init__()
        self.os_details = OSInfo()
        self.meminfo = MemInfo()
        self.update()

    @property
    def cpus(self):
        """CPU count

        """
        return len(self.cpuinfo)

    @property
    def total_memory(self):
        """Total memory

        """
        return self.meminfo['MemTotal']

    @property
    def release(self):
        """Parse linux release

        """
        self.parse_os_details()
        try:
            return self.os_details['PRETTY_NAME']
        except KeyError:
            return None

    def parse_os_details(self):
        """Parse /etc/os-release

        """
        self.os_details.clear()
        try:
            with open('/etc/os-release', 'r') as f:
                for line in [line.strip() for line in f.readlines()]:
                    try:
                        key, value = line.split('=')
                        value = value.strip('"')
                        self.os_details[key] = value
                    except:
                        pass
        except Exception as e:
            pass

    def parse_meminfo(self):
        """Memory info

        """
        self.meminfo.clear()
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in [line.rstrip() for line in f.readlines()]:
                    try:
                        key, value = [v.strip() for v in line.split(':', 1)]
                        self.meminfo[key] = value
                    except:
                        pass
        except OSError:
            pass
        except IOError:
            pass


    def parse_cpuinfo(self):
        """CPU info

        Processor core count based on /proc/cpuinfo
        """
        self.cpuinfo = []

        try:
            processor = None
            with open('/proc/cpuinfo', 'r') as f:
                for line in [line.rstrip() for line in f.readlines()]:
                    try:
                        key, value = [v.strip() for v in line.split(':')]
                        if key == 'processor':
                            processor = CPUInfo(index=int(value))
                            self.cpuinfo.append(processor)
                        elif processor is not None:
                            processor[key] = value
                    except:
                        pass
        except OSError:
            pass
        except IOError:
            pass

    def update(self):
        """Update details

        """
        super(SystemInformation, self).update()
        self.parse_dmi()
        self.parse_cpuinfo()
        self.parse_meminfo()
        self.parse_os_details()

    def as_dict(self, verbose=False):
        data = super(SystemInformation, self).as_dict()
        if verbose:
            data['cpuinfo'] = self.cpuinfo
            data['osinfo'] = self.os_details
            data['meminfo'] = self.meminfo
        return data

    def to_json(self, verbose=False):
        data = self.as_dict(verbose=verbose)
        return json.dumps(data, indent=2, cls=self.json_encoder)
