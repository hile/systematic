"""
Parsing of smartctl command output information
"""
from __future__ import unicode_literals

import configobj
import fnmatch
import json
import os
import re
import sys

from builtins import int, str
from datetime import datetime
from systematic.stats import StatsParser, StatsParserError
from systematic.shell import CONFIG_PATH

SYSTEM_CONFIG_PATHS = (
    '/etc/systematic/smartdevices.conf',
    '/usr/local/etc/systematic/smartdevices.conf',
)

HEADERS = {
    'version': re.compile(
        r'^smartctl\s+(?P<version>[^\s]+)\s+(?P<date>[0-9-]+)\s+(?P<release>[^\s]+)\s+(?P<build>.*)$'
    ),
    'copyright': re.compile(r'^Copyright\s+\(C\)\s+(?P<copyright>.*)$'),
}

INFO_FIELD_MAP = {
    'ATA Version is':       'ATA version',
    'Device Model':         'Device model',
    'Firmware Version':     'Firmware version',
    'LU WWN Device Id':     'LU WWN device ID',
    'Local Time is':        'Date',
    'Model Family':         'Model family',
    'Rotation Rate':        'Rotation rate',
    'SATA Version is':      'SATA version',
    'Sector Sizes':         'Sector sizes',
    'Sector Size':          'Sector size',
    'Serial Number':        'Serial number',
    'User Capacity':        'User capacity',
    'SMART support is':     'SMART support status',
}

INFO_FIELD_PARSERS = {
    'Date': lambda x: datetime.strptime(x, '%a %b %d %H:%M:%S %Y %Z'),
    'SMART status': lambda x: x == 'Enabled',
    'User capacity': lambda x: int(x.replace(',', '').split()[0]),
}

INFO_COMMON_FIELDS = (
    'Device model',
    'Serial number',
    'Firmware version',
    'Model family',
    'User capacity',
    'Sector size',
    'Sector sizes',
)

ATTRIBUTE_FIELD_NAME_MAP = {
    'airflow_temperature_cel':      'Airflow temperature',
    'calibration_retry_count':      'Calibration retries',
    'current_pending_sector':       'Current pending sectors',
    'crc_error_count':              'CRC errors',
    'ecc_error_rate':               'ECC error rate',
    'end-to-end_error':             'End-to-end errors',
    'erase_fail_count':             'Erase fail',
    'erase_fail_count_total':       'Erase fail total',
    'g-sense_error_rate':           'G-sense error rate',
    'high_fly_writes':              'High-fly writes',
    'load_cycle_count':             'Load cycles',
    'multi_zone_error_rate':        'Multi-Zone error rate',
    'reallocated_sector_ct':        'Reallocated sectors',
    'power_on_hours':               'Power on hours',
    'power_cycle_count':            'Power cycles',
    'power-off_retract_count':      'Power-off retracts',
    'program_fail_count':           'Program failures',
    'program_fail_cnt_total':       'Program failures total',
    'offline_uncorrectable':        'Offline uncorrectable',
    'raw_read_error_rate':          'Raw read error rate',
    'reallocated_event_count':      'Reallocated events',
    'reported_uncorrect':           'Reported uncorrectable',
    'retired_block_count':          'Retired blocks',
    'runtime_bad_block':            'Runtibe bad blocks',
    'por_recovery_count':           'POR recoveries',
    'seek_error_rate':              'Seek error rate',
    'spin_retry_count':             'Spin retries',
    'spin_up_time':                 'Spin up time',
    'start_stop_count':             'Start-stop count',
    'temperature_celsius':          'Temperature',
    'total_lbas_written':           'Total LBAs written',
    'total_lbas_read':              'Total LBAs read',
    'udma_crc_error_count':         'UDMA CRC errors',
    'uncorrectable_error_cnt':      'Uncorrectable errors',
    'unexpect_power_loss_ct':       'Unexpected power losses',
    'unexpected_power_loss_count':  'Unexpected power losses',
    'used_rsvd_blk_cnt_tot':        'Used reserved blocks total',
    'wear_leveling_count':          'Wear levelings',
}

ATTRIBUTE_FIELD_MAP_PARSERS = {
    'attribute_name': lambda x: x.lower(),
    'failed': lambda x: x != '-',
    'type': lambda x: x.lower(),
    'updated': lambda x: x.lower(),
}

ATTRIBUTE_COMMON_FIELDS = (
    'power_on_hours',
    'total_lbas_written',
    'total_lbas_read',
    'airflow_temperature_cel',
    'temperature_celsius',

    'raw_read_error_rate',
    'seek_error_rate',
    'uncorrectable_error_cnt',
    'crc_error_count',
    'udma_crc_error_count',
    'ecc_error_rate',
)

SMART_UNSUPPORTED_PATTERNS = (
    re.compile('^Unavailable - (?P<status>.*)$'),
)

PLATFORM_IGNORED_DEVICE_MATCHES = {
    'freebsd9': [
        re.compile('r^/dev/ses[0-9]+$'),
    ],
    'freebsd10': [
        re.compile('r^/dev/ses[0-9]+$'),
    ],
    'freebsd11': [
        re.compile('r^/dev/ses[0-9]+$'),
    ],
}

RE_SECTOR_SIZE = re.compile(r'(?P<size>\d+) bytes logical/physical')
RE_SECTOR_SIZES = re.compile(r'(?P<logical>\d+) bytes logical, (?P<physical>\d+) bytes physical')


class SmartError(Exception):
    pass


class SmartInfoField(object):
    """SMART info

    SMART info for a drive, parsing the free-form text details
    """
    def __init__(self, drive, field, value):
        self.drive = drive
        self.field = field
        self.value = value

    def __repr__(self):
        return '{0}'.format(self.value)


class SmartAttribute(dict):
    """SMART attribute

    SMART counter attribute for drive
    """
    def __init__(self, drive, name, description, **attributes):
        self.drive = drive
        self.name = name
        self.description = description
        self.update(**attributes)

    def __repr__(self):
        return '{0} {1}'.format(self.description, self['raw_value'])


class SmartDrive(object):
    """SMART drive

    One drive in SMART data
    """

    def __init__(self, client, device, flags=None):
        self.client = client
        self.device = device
        self.driver = self.client.config.get_driver(self.device)
        self.name = str(os.path.basename(device))
        self.flags = flags if flags is not None else []

    def __repr__(self):
        return self.device

    def __eq__(self, other):
        if isinstance(other, str):
            return self.device == other
        return self.device == other.device

    def __ne__(self, other):
        if isinstance(other, str):
            return self.device != other
        return self.device != other.device

    def __gt__(self, other):
        if isinstance(other, str):
            return self.device > other
        return self.device > other.device

    def __le__(self, other):
        if isinstance(other, str):
            return self.device <= other
        return self.device <= other.device

    def __lt__(self, other):
        if isinstance(other, str):
            return self.device < other
        return self.device < other.device

    def __ge__(self, other):
        if isinstance(other, str):
            return self.device >= other
        return self.device >= other.device

    def __re_line_matches__(self, regexp, lines):
        """Lines pattern matching

        Returns re groupdict matches for lines matching regexp
        """
        matches = []

        for line in lines:
            m = regexp.match(line)
            if not m:
                continue
            matches.append(m.groupdict())

        return matches

    @property
    def is_supported(self):
        """Check if drive is supported

        """
        try:
            return self.get_info()['SMART support status'].value.strip() == 'Enabled'
        except:  # noqa
            return False

    @property
    def is_healthy(self):
        """Return True if drive is healthy

        Currently health check just checks if health status is 'PASSED'
        """

        re_result = re.compile(r'^SMART overall-health self-assessment test result: (?P<status>.*)$')
        try:
            if self.driver:
                cmd = ('smartctl', '-d', self.driver, '--health', self.device)
            else:
                cmd = ('smartctl', '--health', self.device)
            matches = self.__re_line_matches__(re_result, self.client.execute(cmd))
        except SmartError:
            return False

        if not matches:
            return False
        status = matches[0]['status']
        return status in ['PASSED'] and True or False

    def get_attributes(self):
        """Smart attributes

        Return smart attributes for drive
        """

        attributes = {}

        re_match = re.compile(r'^{0}$'.format(r'\s+'.join([
            r'(?P<id>0x[0-9a-f]+)',
            r'(?P<attribute_name>[^\s]+)',
            r'(?P<flag>0x[0-9a-f]+)',
            r'(?P<value>0x[0-9a-f]+)',
            r'(?P<worst>0x[0-9a-f]+)',
            r'(?P<threshold>0x[0-9a-f]+)',
            r'(?P<type>[^\s]+)',
            r'(?P<updated>[^\s]+)',
            r'(?P<failed>[^\s]+)',
            r'(?P<raw_value>[0-9a-f]+)',
        ])))

        try:
            if self.driver:
                cmd = ('smartctl', '-d', self.driver, '--format=hex', '--attributes', self.device)
            else:
                cmd = ('smartctl', '--format=hex', '--attributes', self.device)
            matches = self.__re_line_matches__(re_match, self.client.execute(cmd))
        except SmartError:
            return attributes

        for m in matches:

            if 'attribute_name' not in m:
                continue

            name = m['attribute_name']
            del m['attribute_name']
            try:
                description = ATTRIBUTE_FIELD_NAME_MAP[name.lower()]
            except KeyError:
                description = name

            for k in ('id', 'flag', 'value', 'worst', 'threshold'):
                m[k] = int(m[k], 16)

            m['raw_value'] = int(m['raw_value'])

            for k in m.keys():
                if k not in ATTRIBUTE_FIELD_MAP_PARSERS.keys():
                    continue
                m[k] = ATTRIBUTE_FIELD_MAP_PARSERS[k](m[k])

            attributes[name.lower()] = SmartAttribute(self, name, description, **m)

        return attributes

    def get_overview(self):
        """Return common info fields

        Returns common info fields in default order
        """
        info = self.get_info()

        fields = []
        for key in INFO_COMMON_FIELDS:
            try:
                fields.append(info[key])
            except KeyError:
                continue

        return fields

    def get_info(self):
        """Return drive info

        Returns all known info fields
        """
        def parse_sector_sizes(value):
            """Parse different sector size presentations

            """
            m = RE_SECTOR_SIZE.match(value)
            if m:
                return {
                    'logical': int(m.groupdict()['size']),
                    'physical': int(m.groupdict()['size']),
                }
            m = RE_SECTOR_SIZES.match(value)
            if m:
                return dict((k, int(v)) for k, v in m.groupdict().items())
            return value

        re_result = re.compile(r'^(?P<field>[^:]+):\s+(?P<value>.*)$')
        details = {}

        try:
            if self.driver:
                cmd = ('smartctl', '-d', self.driver, '--info', self.device)
            else:
                cmd = ('smartctl', '--info', self.device)
            matches = self.__re_line_matches__(re_result, self.client.execute(cmd))
        except SmartError:
            return details

        for m in matches:

            try:
                name = INFO_FIELD_MAP[m['field']]
            except KeyError:
                continue

            if name in INFO_FIELD_PARSERS.keys():
                value = INFO_FIELD_PARSERS[name](m['value'])
            else:
                value = m['value']

            if name in ('Sector size', 'Sector sizes'):
                value = parse_sector_sizes(value)
                details['Sector sizes'] = SmartInfoField(self, 'Sector sizes', value)
            else:
                details[name] = SmartInfoField(self, name, value)

        return details

    def set_smart_status(self, enabled):
        """Set SMART enabled status

        Enable or disable SMART on drive
        """
        if self.driver:
            cmd = ('smartctl', '-d', self.driver, '--smart={0}'.format(enabled and 'on' or 'off', self.device))
        else:
            cmd = ('smartctl', '--smart={0}'.format(enabled and 'on' or 'off', self.device))
        self.client.execute(cmd)

    def set_offline_testing(self, enabled):
        """Set SMART offline testing status

        Enable or disable SMART offline testing on drive
        """
        if self.driver:
            cmd = ('smartctl', '-d', self.driver, '--offlineauto={0}'.format(enabled and 'on' or 'off', self.device))
        else:
            cmd = ('smartctl', '--offlineauto={0}'.format(enabled and 'on' or 'off', self.device))
        self.client.execute(cmd)

    def set_attribute_autosave(self, enabled):
        """Set SMART attribute autosave

        Enable or disable SMART attribute autosave on drive
        """
        if self.driver:
            cmd = ('smartctl', '-d', self.driver, '--saveauto={0}'.format(enabled and 'on' or 'off', self.device))
        else:
            cmd = ('smartctl', '--saveauto={0}'.format(enabled and 'on' or 'off', self.device))
        self.client.execute(cmd)

    def as_dict(self, verbose=False):
        """Return drive status as dict

        """
        info = self.get_info()
        if not info:
            raise SmartError('Drive does not seem to support SMART')

        data = {
            'device': self.device,
            'healthy': self.is_healthy,
            'supported': self.is_supported,
            'info': dict((k, '{0}'.format(v)) for k, v in info.items()),
        }

        if verbose:
            data['attributes'] = self.get_attributes()
            data['flags'] = self.flags

        return data


class SmartCtlConfig(object):
    """Configuration for SmartCtlClient

    Parse configuration smartdevices.conf for SmartCtlClient.

    This is used to set explicit driver for certain devices.
    """
    def __init__(self, path=None, load_system_config=True):
        self.drivers = {}

        # Allow disabling loading of system configuration for tests
        if load_system_config:
            for filename in SYSTEM_CONFIG_PATHS:
                if os.path.isfile(filename):
                    self.load(filename)

            path = path is not None and path or os.path.join(CONFIG_PATH, 'smartdevices.conf')
            if os.path.isfile(os.path.realpath(path)):
                self.load(path)

    def load(self, path):
        """Load configuration

        Raises SmartError if configuration could not be loaded.
        """
        try:
            # Driver can be like 'usbjmicron,0' so skip list values
            data = configobj.ConfigObj(path, list_values=False)
        except Exception as e:
            raise SmartError('Error reading {0}: {1}'.format(path, e))

        if 'drivers' in data:
            self.drivers.update(data['drivers'])

    def get_driver(self, device):
        """Get driver for device

        Return driver matching device path or None if not configured
        """
        for key in self.drivers:
            if fnmatch.fnmatch(device, key):
                return self.drivers[key]
        return None


class SmartCtlClient(StatsParser):
    """Client for smartctl

    API to enumerate SMART supported drives
    """
    parser_name = 'smart'

    def __init__(self, *args, **kwargs):
        self.drives = []
        if 'config' in kwargs:
            self.config = SmartCtlConfig(path=kwargs['config'])
            del kwargs['config']
        else:
            self.config = SmartCtlConfig(load_system_config=kwargs.get('load_system_config', True))
        super(SmartCtlClient, self).__init__(*args, **kwargs)

    def execute(self, args):
        """Execute smartctl commands

        Generic wrapper to execute smartctl commands
        """

        try:
            stdout, stderr = super(SmartCtlClient, self).execute(args)
        except StatsParserError as e:
            raise SmartError('Error executing {0}: {1}'.format(' '.join(args), e))

        headers = {}
        lines = []
        for line in stdout.split('\n'):

            matched = False
            for name, re_header in HEADERS.items():
                m = re_header.match(line)
                if m:
                    headers[name] = m.groupdict()
                    matched = True
                    break

            if not matched:
                lines.append(line)

        return lines

    def is_ignored(self, device):
        """Check if given drive is ignored

        Certain SMART supported drives are ignored on some platforms by device name
        """

        if sys.platform not in PLATFORM_IGNORED_DEVICE_MATCHES.keys():
            return False

        for m in PLATFORM_IGNORED_DEVICE_MATCHES[sys.platform]:
            if m.match(device):
                return True

        return False

    def find_drive(self, device):
        """Find drive by name

        Matches device name with full path or basename, returns drive if found or None
        """
        for drive in self.drives:
            if isinstance(device, SmartDrive):
                if drive == device:
                    return drive

            elif drive.device == device or drive.name == os.path.basename(device):
                return drive

        return None

    def scan(self):
        """Scan for drivers

        Compatibility call - use self.update()
        """
        return self.update()

    def update(self):
        """Scan for drives

        Scan for smart drives. May return invalid drives that don't actually support S.M.A.R.T.
        """
        self.drives = []

        try:
            output = self.execute(('smartctl', '--scan'))
        except SmartError as e:
            raise SmartError('Error scanning S.M.A.R.T. drives: {0}'.format(e))

        for line in [line.strip() for line in output if line.strip() != '']:

            try:
                data, comment = [str(x.strip()) for x in line.split('#', 1)]
                device, flags = [str(x.strip()) for x in data.split(None, 1)]
                flags = flags.split()
                if not self.is_ignored(device):
                    self.drives.append(SmartDrive(self, device, flags))

            except ValueError:
                raise SmartError('Error parsing line from output: {0}'.format(line))

        # Add explicitly configured drives
        for device in self.config.drivers:
            device = str(device)
            self.drives.append(SmartDrive(self, device, flags=[]))

        self.drives.sort()
        return self.update_timestamp()

    def as_dict(self, verbose=False):
        """Return data as dict

        """
        if self.__updated__ is None:
            self.update()
        data = {
            'timestamp': self.__updated__,
            'drives': [],
        }
        for drive in self.drives:
            if not drive.is_supported:
                continue
            data['drives'].append(drive.as_dict(verbose=verbose))
        return data

    def to_json(self, verbose=False):
        """Return SMART data as JSON

        """
        if len(self.drives) == 0:
            self.update()
        return json.dumps(self.as_dict(verbose=verbose), indent=2)
