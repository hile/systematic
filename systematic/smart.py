"""
Parsing of smartctl command output information
"""

import os
import re
import sys

from datetime import datetime,timedelta
from systematic.classes import check_output, CalledProcessError
from systematic.shell import CommandPathCache

commands = CommandPathCache()
commands.update()

HEADERS = {
    'version': re.compile('^smartctl\s+(?P<version>[^\s]+)\s+(?P<date>[0-9-]+)\s+(?P<release>[^\s]+)\s+(?P<build>.*)$'),
    'copyright': re.compile('^Copyright\s+\(C\)\s+(?P<copyright>.*)$'),
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
    'SMART support is':     'SMART status',
    'Sector Sizes':         'Sector sizes',
    'Sector Size':          'Sector size',
    'Serial Number':        'Serial number',
    'User Capacity':        'User capacity',
}

INFO_FIELD_PARSERS = {
    'Date':                 lambda x: datetime.strptime(x, '%a %b %d %H:%M:%S %Y %Z'),
    'SMART status':         lambda x: x == 'Enabled',
    'User capacity':        lambda x: long(x.replace(',', '').split()[0]),
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
    'erase_fail_count':             'Erase fail',
    'erase_fail_count_total':       'Erase fail total',
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
    'POR_Recovery_Count':           'POR recoveries',
    'seek_error_rate':              'Seek error rate',
    'spin_retry_count':             'Spin retries',
    'spin_up_time':                 'Spin up time',
    'start_stop_count':             'Start-stop count',
    'temperature_celsius':          'Temperature',
    'total_lbas_written':           'Total LBAs written',
    'udma_crc_error_count':         'UDMA CRC errors',
    'uncorrectable_error_cnt':      'Uncorrectable errors',
    'unexpect_power_loss_ct':       'Unexpected power losses',
    'unexpected_power_loss_count':  'Unexpected power losses',
    'used_rsvd_blk_cnt_tot':        'Used reserved blocks total',
    'wear_leveling_count':          'Wear levelings',
}

ATTRIBUTE_FIELD_MAP_PARSERS = {
    'attribute_name':       lambda x: x.lower(),
    'failed':               lambda x: x != '-',
    'type':                 lambda x: x.lower(),
    'updated':              lambda x: x.lower(),
}

ATTRIBUTE_COMMON_FIELDS = (
    'power_on_hours',
    'total_lbas_written',
    'airflow_temperature_cel',
    'temperature_celsius',
    'seek_error_rate',
    'uncorrectable_error_cnt',
    'crc_error_count',
    'udma_crc_error_count',
    'ecc_error_rate',
)


PLATFORM_IGNORED_DEVICE_MATCHES = {
    'freebsd9': [
        re.compile('^/dev/ses[0-9]+$'),
    ],
    'freebsd10': [
        re.compile('^/dev/ses[0-9]+$'),
    ],
}


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

    def __init__(self, client, device, flags=[]):
        self.client = client
        self.device = device
        self.name = os.path.basename(device)

    def __repr__(self):
        return self.device

    def __cmp__(self, other):
        if isinstance(other, basestring):
            return cmp(self.device, other)
        return cmp(self.device, other.device)

    def __re_line_matches__(self, regexp, lines):
        """Lines pattern matching

        Returns re groupdict matches for lines matching regexp
        """
        matches = []

        for l in lines:
            m =regexp.match(l)
            if not m:
                continue
            matches.append(m.groupdict())

        return matches

    @property
    def is_healthy(self):
        """Return True if drive is healthy

        Currently health check just checks if health status is 'PASSED'
        """

        re_result = re.compile('^SMART overall-health self-assessment test result: (?P<status>.*)$')
        matches = self.__re_line_matches__(re_result, self.client.execute([ 'smartctl', '--health', self.device ]))
        if not matches:
            raise SmartError('Did not receive health status line in output')

        status = matches[0]['status']
        return status in ['PASSED'] and True or False

    def get_attributes(self):
        """Smart attributes

        Return smart attributes for drive
        """

        re_match = re.compile('^{0}$'.format('\s+'.join([
            '(?P<id>0x[0-9a-f]+)',
            '(?P<attribute_name>[^\s]+)',
            '(?P<flag>0x[0-9a-f]+)',
            '(?P<value>0x[0-9a-f]+)',
            '(?P<worst>0x[0-9a-f]+)',
            '(?P<threshold>0x[0-9a-f]+)',
            '(?P<type>[^\s]+)',
            '(?P<updated>[^\s]+)',
            '(?P<failed>[^\s]+)',
            '(?P<raw_value>[0-9a-f]+)',
        ])))
        matches = self.__re_line_matches__(re_match,
            self.client.execute([ 'smartctl', '--format=hex', '--attributes', self.device ])
        )

        attributes = {}
        for m in matches:

            if 'attribute_name' not in m:
                continue

            name = m['attribute_name']
            try:
                description = ATTRIBUTE_FIELD_NAME_MAP[m['attribute_name'].lower()]
            except KeyError:
                description = name

            for k in ('id','flag','value','worst','threshold'):
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

        re_result = re.compile('^(?P<field>[^:]+):\s+(?P<value>.*)$')
        matches = self.__re_line_matches__(re_result, self.client.execute([ 'smartctl', '--info', self.device ]))

        details = {}
        for m in matches:

            try:
                name = INFO_FIELD_MAP[m['field']]
            except KeyError:
                continue

            if name in INFO_FIELD_PARSERS.keys():
                value = INFO_FIELD_PARSERS[name](m['value'])
            else:
                value = m['value']

            details[name] = SmartInfoField(self, name, value)

        return details

    def set_smart_status(self, enabled):
        """Set SMART enabled status

        Enable or disable SMART on drive
        """
        self.client.execute( [ 'smartctl', '--smart={0}'.format(enabled and 'on' or 'off', self.device) ] )

    def set_offline_testing(self, enabled):
        """Set SMART offline testing status

        Enable or disable SMART offline testing on drive
        """
        execute( [ 'smartctl', '--offlineauto={0}'.format(enabled and 'on' or 'off', self.device) ] )

    def set_attribute_autosave(self, enabled):
        """Set SMART attribute autosave

        Enable or disable SMART attribute autosave on drive
        """
        execute( [ 'smartctl', '--saveauto={0}'.format(enabled and 'on' or 'off', self.device) ] )


class SmartCtlClient(object):
    """Client for smartctl

    API to enumerate SMART supported drives
    """

    def __init__(self):
        if not commands.which('smartctl'):
            raise SmartError('No such command: smartctl')
        self.drives = []

    def execute(self, command):
        """Execute smartctl commands

        Generic wrapper to execute smartctl commands
        """

        try:
            output = check_output(command)
        except CalledProcessError,emsg:
            raise SmartError('Error executing {0}: {1}'.format(' '.join(command), emsg))

        headers = {}
        lines = []
        for l in output.split('\n'):

            matched = False
            for name,re_header in HEADERS.items():
                m = re_header.match(l)
                if m:
                    headers[name] = m.groupdict()
                    matched = True
                    break

            if not matched:
                lines.append(l)

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
        """Scan for drives

        Scan for smart drives
        """

        self.drives = []

        for line in [line.strip() for line in self.execute( ['smartctl', '--scan' ] ) if line.strip() != '']:

            try:
                data, comment = [x.strip() for x in line.split('#', 1)]
                device, flags = [x.strip() for x in data.split(None, 1)]
                flags = flags.split()
                if not self.is_ignored(device):
                    self.drives.append(SmartDrive(self, device, flags))

            except ValueError:
                raise SmartError('Error parsing line from output: {0}'.format(line))

        self.drives.sort()
