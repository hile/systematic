"""
Parsing of smartctl command output information
"""

import re

from datetime import datetime,timedelta
from subprocess import check_output,CalledProcessError,Popen,PIPE
from systematic.shell import CommandPathCache

commands = CommandPathCache()
commands.update()

CMD = 'smartctl'
HEADERS = {
    'version': re.compile('^smartctl\s+(?P<version>[^\s]+)\s+(?P<date>[0-9-]+)\s+(?P<release>[^\s]+)\s+(?P<build>.*)$'),
    'copyright': re.compile('^Copyright\s+\(C\)\s+(?P<copyright>.*)$'),
}
INFO_FIELD_MAP = {
    'ATA Version is':       'ata_version',
    'Device Model':         'device_model',
    'Device is':            'device_smart',
    'Firmware Version':     'firmware_version',
    'LU WWN Device Id':     'lu_wwn_device_id',
    'Local Time is':        'local_time',
    'Model Family':         'model_family',
    'Rotation Rate':        'rpm',
    'SATA Version is':      'smart_version',
    'SMART support is':     'smart_support',
    'Sector Sizes':         'sector_sizes',
    'Sector Size':          'sector_size',
    'Serial Number':        'serial_number',
    'User Capacity':        'user_capacity',
}
INFO_FIELD_PARSERS = {
    'local_time':           lambda x: datetime.strptime(x,'%a %b %d %H:%M:%S %Y %Z'),
    'smart_support':        lambda x: x=='Enabled',
    'user_capacity':        lambda x: long(x.replace(',','').split()[0]),
}

ATTRIBUTE_FIELD_NAME_MAP = {
    'airflow_temperature_cel':  'airflow_temperature',
    'calibration_retry_count':  'calibration_retries',
    'current_pending_sector':   'pending_sectors',
    'erase_fail_count':         'erase_failures',
    'erase_fail_count_total':   'total_erase_failures',
    'load_cycle_count':         'load_cycles',
    'reallocated_sector_ct':    'reallocated_sectors',
    'unexpect_power_loss_ct':   'unexpected_power_loss_count',
    'power_cycle_count':        'power_cycles',
    'power-off_retract_count':  'power_off_retracts',
    'program_fail_count':       'program_failures',
    'program_fail_cnt_total':   'total_program_failures',
    'reallocated_event_count':  'reallocated_events',
    'reported_uncorrect':       'reported_uncorrectable',
    'retired_block_count':      'retired_blocks',
    'runtime_bad_block':        'runtime_bad_blocks',
    'spin_retry_count':         'spin_retries',
    'start_stop_count':         'start_stop_cycles',
    'total_lbas_written':       'total_lba_write',
    'udma_crc_error_count':     'udma_crc_errors',
    'unexpected_power_loss_count': 'unexpected_power_loss',
    'used_rsvd_blk_cnt_tot':    'total_used_reserved_blocks',
    'wear_leveling_count':      'wear_leveling_cycles',
}

ATTRIBUTE_FIELD_MAP_PARSERS = {
    'attribute_name':       lambda x: x.lower(),
    'failed':               lambda x: x!='-',
    'type':                 lambda x: x.lower(),
    'updated':              lambda x: x.lower(),
}

PLATFORM_IGNORED_DEVICE_MATCHES = {
    'freebsd9':     [
        re.compile('^/dev/ses[0-9]+$'),
    ],
}


class SmartError(Exception):
    def __str__(self):
        return self.args[0]


def execute(command):
    if not isinstance(command,list):
        raise SmartError('Command to execute must be a list')

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


class SmartDrive(object):
    def __init__(self,device,flags=[]):
        self.device = device

    def __str__(self):
        return self.device

    def __re_line_matches__(self,regexp,lines):
        matches = []

        for l in lines:
            m =regexp.match(l)
            if not m:
                continue
            matches.append(m.groupdict())

        return matches

    @property
    def attributes(self):
        re_string = '^{0}$'.format('\s+'.join([
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
        ]))

        re_result = re.compile(re_string)
        matches = self.__re_line_matches__(re_result,execute([CMD,'--format=hex','--attributes',self.device]))
        fields = []
        for m in matches:
            for k in ('id','flag','value','worst','threshold'):
                m[k] = int(m[k],16)
            m['raw_value'] = int(m['raw_value'])

            for k in m.keys():
                if k not in ATTRIBUTE_FIELD_MAP_PARSERS.keys():
                    continue
                m[k] = ATTRIBUTE_FIELD_MAP_PARSERS[k](m[k])

            if m['attribute_name'] in ATTRIBUTE_FIELD_NAME_MAP.keys():
                m['attribute_name'] = ATTRIBUTE_FIELD_NAME_MAP[m['attribute_name']]

            fields.append(m)

        fields.sort(lambda x,y: cmp(x['attribute_name'],y['attribute_name']))

        return fields

    @property
    def info(self):
        re_result = re.compile('^(?P<field>[^:]+):\s+(?P<value>.*)$')
        matches = self.__re_line_matches__(re_result,execute([CMD,'--info',self.device]))
        details = {}

        for m in matches:
            if m['field'] in INFO_FIELD_MAP.keys():
                field = INFO_FIELD_MAP[m['field']]
                if field in INFO_FIELD_PARSERS.keys():
                    value = INFO_FIELD_PARSERS[field](m['value'])
                else:
                    value = m['value']
                details[field] = value
            else:
                details[m['field']] = m['value']

        return details

    @property
    def health_status(self):
        re_result = re.compile('^SMART overall-health self-assessment test result: (?P<status>.*)$')

        matches = self.__re_line_matches__(re_result,execute([CMD,'--health',self.device]))
        if not matches:
            raise SmartError('Did not receive health status line in output')

        status = matches[0]['status']
        health = status in ['PASSED'] and True or False
        return health,status

    def get_attribute_by_id(self,attribute_id):
        if not isinstance(attribute_id,int):

            try:
                attribute_id = int(attribute_id)

            except ValueError:
                try:
                    attribute_id = int(attribute_id,16)
                except ValueError:
                    raise SmartError('Invalid attribute_id value: {0}'.format(attribute_id))

        for attr in self.attributes:
            if attr['id'] == attribute_id:
                return attr

        return None

    def set_smart_status(self,status):
        status = status and 'on' or 'off'
        execute([CMD,'--smart={0}'.format(status, self.device)])

    def set_offline_testing(self,status):
        status = status and 'on' or 'off'
        execute([CMD,'--offlineauto={0}'.format(status, self.device)])

    def set_attribute_autosave(self,status):
        status = status and 'on' or 'off'
        execute([CMD,'--saveauto={0}'.format(status, self.device)])


class SmartDevices(list):
    def __init__(self):
        if not commands.which(CMD):
            raise SmartError('No such command: {0}'.format(CMD))
        self.scan()

    def is_ignored(self,device):
        if sys.platform not in PLATFORM_IGNORED_DEVICE_MATCHES.keys():
            return False

        for m in PLATFORM_IGNORED_DEVICE_MATCHES[sys.platform]:
            if m.match(device):
                return True

        return False

    def scan(self):
        cmd = [CMD,'--scan']

        for l in [l.strip() for l in execute(cmd) if l.strip()!='']:

            try:
                data,comment = [x.strip() for x in l.split('#',1)]
                device,flags = [x.strip() for x in data.split(None,1)]
                flags = flags.split()
                if not self.is_ignored(device):
                    self.append(SmartDrive(device,flags))

            except ValueError:
                raise SmartError('Error parsing line from output: {0}'.format(l))
