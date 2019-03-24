"""
Parse dmidecode output

Example usage:

from systematic.stats.hardware.dmi import DMI
dmi = DMI()
print(dmi.to_json())

"""
from __future__ import unicode_literals

import json
import re

from builtins import int, str  # noqa

from systematic.stats import StatsParser, StatsParserError

RE_VERSION = re.compile(r'^#\s+dmidecode\s+(?P<version>.*)$')
RE_TABLE_START = re.compile(r'^Table at (?P<address>.*).')
RE_HANDLE_START = re.compile(
    r'^Handle\s+(?P<offset>[x0-9a-fA-F]+),\s+DMI\s+type\s+(?P<handle_type>\d+),\s+(?P<handle_bytes>\d+) bytes$'
)

# DMI handle type mapping
DMI_HANDLE_TYPE_MAP = {
    0:   'BIOS',
    1:   'System',
    2:   'Base Board',
    3:   'Chassis',
    4:   'Processor',
    5:   'Memory Controller',
    6:   'Memory Module',
    7:   'Cache',
    8:   'Port Connector',
    9:   'System Slots',
    10:  'On Board Devices',
    11:  'OEM Strings',
    12:  'System Configuration Options',
    13:  'BIOS Language',
    14:  'Group Associations',
    15:  'System Event Log',
    16:  'Physical Memory Array',
    17:  'Memory Device',
    18:  '32-bit Memory Error',
    19:  'Memory Array Mapped Address',
    20:  'Memory Device Mapped Address',
    21:  'Built-in Pointing Device',
    22:  'Portable Battery',
    23:  'System Reset',
    24:  'Hardware Security',
    25:  'System Power Controls',
    26:  'Voltage Probe',
    27:  'Cooling Device',
    28:  'Temperature Probe',
    29:  'Electrical Current Probe',
    30:  'Out-of-band Remote Access',
    31:  'Boot Integrity Services',
    32:  'System Boot',
    33:  '64-bit Memory Error',
    34:  'Management Device',
    35:  'Management Device Component',
    36:  'Management Device Threshold Data',
    37:  'Memory Channel',
    38:  'IPMI Device',
    39:  'Power Supply',
    41:  'On Board Devices',
    139: 'OEM-specific Type',
}


class DMIError(Exception):
    pass


class DMIProperty(dict):
    """DMI property

    DMI handle data property
    """
    def __init__(self, handle, name, value=''):
        self.handle = handle
        self.name = name
        self.value = value
        self.options = []

    def __repr__(self):
        return '{0}={1}'.format(self.name, self.value)

    def add_option(self, value):
        self.options.append(value)

    def as_dict(self):
        """Format property as dict

        """
        return {
            'name': self.name,
            'value': self.value,
            'options': self.options,
        }


class DMIHandle(object):
    """DMI handle

    """
    def __init__(self, table, offset, handle_type, handle_bytes):
        self.table = table
        self.offset = int(offset, 16)
        self.handle_type = int(handle_type)
        self.handle_bytes = int(handle_bytes)
        self.properties = []

    def __repr__(self):
        return '"{0}" offset {1}, type {2}, {3} bytes'.format(
            self.name,
            self.offset,
            self.handle_type,
            self.handle_bytes,
        )

    @property
    def name(self):
        """Handle name

        """
        try:
            return DMI_HANDLE_TYPE_MAP[self.handle_type]
        except KeyError:
            return u'UNKNOWN'

    def add_property(self, name, value=''):
        prop = DMIProperty(self, name, value)
        self.properties.append(prop)
        return prop

    def as_dict(self):
        """Format handle as dict

        """
        return {
            'offset': '0x{0:04X}'.format(self.offset),
            'type': self.handle_type,
            'name': self.name,
            'bytes': self.handle_bytes,
            'properties': [prop.as_dict() for prop in self.properties]
        }


class DMITable(object):
    """DMI table

    """
    def __init__(self, address):
        self.address = address
        self.handles = []

    def __repr__(self):
        return 'DMI table {0}'.format(self.address)

    def add_handle(self, handle):
        """Add handle to table

        """
        self.handles.append(handle)

    def as_dict(self):
        """Format table as dict

        """
        return {
            'address': self.address,
            'handles': [handle.as_dict() for handle in self.handles]
        }


class DMI(StatsParser):
    """DMI parser with dmidecode

    """
    parser_name = 'dmi'

    def __init__(self):
        super(DMI, self).__init__()
        self.version = None
        self.tables = []

    def __parse_lines__(self, lines):
        """Iterator to yield parsed lines

        """

        table = None
        handle = None
        prop = None

        for line in lines:
            if line.strip() == '':
                continue

            m = RE_VERSION.match(line.strip())
            if m and self.version is None:
                self.version = m.groupdict()['version']
                continue

            m = RE_TABLE_START.match(line)
            if m:
                table = DMITable(address=m.groupdict()['address'])
                self.tables.append(table)
                handle = None
                prop = None
                continue

            m = RE_HANDLE_START.match(line)
            if m and table:
                handle = DMIHandle(table, **m.groupdict())
                table.add_handle(handle)
                prop = None
                continue

            if line.startswith('\t'):
                if handle is None:
                    raise DMIError('Property outside of a handle')

                if line.count('\t') == 1:
                    try:
                        prop = handle.add_property(*line.lstrip('\t').split(': ', 1))
                    except:  # noqa
                        prop = handle.add_property(line.lstrip('\t'))

                elif line.count('\t') == 2:
                    if prop is None:
                        raise DMIError('Option outside of a property')
                    prop.add_option(line.lstrip('\t'))

                else:
                    raise DMIError('Error parsing line {0}'.format(line))

                continue

    @property
    def updated(self):
        return self.__updated__

    def parse(self):
        """Parse data

        Compatibility method - jst calls self.update
        """

    def find_handles(self, handle_name=None, handle_type=None):
        """Find DMI handles

        Find DMI handles by name or type
        """
        handles = []
        for table in self.tables:
            for handle in table.handles:
                if handle_name is not None and handle.name != handle_name:
                    continue
                if handle_type is not None and handle.handle_type != handle_type:
                    continue
                handles.append(handle)
        return handles

    def find_properties(self, handle_name, property_name):
        """Find properties

        Find properties by handle name and property name
        """
        properties = []
        for handle in self.find_handles(handle_name):
            for prop in handle.properties:
                if prop.name == property_name:
                    properties.append(prop)
        return properties

    def update(self):
        """Update data

        Run dmidecode and parse output
        """
        self.version = None
        self.tables = []
        try:
            stdout, stderr = self.execute('dmidecode')
        except StatsParserError as e:
            raise StatsParserError('Error running dmidecode: {0}'.format(e))

        self.__parse_lines__(stdout.splitlines())
        return self.update_timestamp()

    def as_dict(self):
        """Return DMI data as dictionary

        """
        if self.__updated__ is None:
            self.update()
        return {
            'timestamp': self.__updated__,
            'version': self.version,
            'tables': [table.as_dict() for table in self.tables]
        }

    def to_json(self):
        """Return DMI data as JSON

        """
        return json.dumps(self.as_dict(), indent=2)
