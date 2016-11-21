"""
Parse dmidecode output

Example usage:

from systematic.dmi import DMI

dmi = DMI()
print(dmi.to_json())

"""

import json
import os
import re

from subprocess import Popen, PIPE

RE_VERSION = re.compile('^#\s+dmidecode\s+(?P<version>.*)$')
RE_TABLE_START = re.compile('^Table at (?P<address>.*).')
RE_HANDLE_START = re.compile('^Handle\s+(?P<offset>[x0-9a-fA-F]+),\s+DMI\s+type\s+(?P<handle_type>\d+),\s+(?P<handle_bytes>\d+) bytes$')


class DMIError(Exception):
    pass


class DMIProperty(dict):
    """DMI property

    """
    def __init__(self, group, name, value=''):
        self.group = group
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

class DMIPropertyGroup(dict):
    """DMI property group

    """
    def __init__(self, handle, name):
        self.handle = handle
        self.name = name
        self.properties = []

    def __repr__(self):
        return self.name

    def add_property(self, name, value=''):
        prop = DMIProperty(self, name, value)
        self.properties.append(prop)
        return prop

    def as_dict(self):
        """Format group as dict

        """
        return {
            'name': self.name,
            'properties': [prop.as_dict() for prop in self.properties]
        }


class DMIHandle(object):
    """DMI handle

    """
    def __init__(self, table, offset, handle_type, handle_bytes):
        self.table = table
        self.offset = int(offset, 16)
        self.handle_type = int(handle_type)
        self.handle_bytes = int(handle_bytes)
        self.groups = []

    def __repr__(self):
        return 'handle {0} type {1} of {2} bytes'.format(
            self.offset,
            self.handle_type,
            self.handle_bytes,
        )

    def add_group(self, name):
        """Add property group

        """
        group = DMIPropertyGroup(self, name)
        self.groups.append(group)
        return group

    def as_dict(self):
        """Format handle as dict

        """
        return {
            'offset': '0x{0:04X}'.format(self.offset),
            'type': self.handle_type,
            'bytes': self.handle_bytes,
            'groups': [group.as_dict() for group in self.groups]
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


class DMI(object):
    """DMI parser with dmidecode

    Runs self.parse() immediately, may raise DMIError as side effect.
    """
    def __init__(self):
        self.version = None
        self.flags = []
        self.tables = []
        self.parse()

    def parse(self):
        """Run dmidecode and parse output

        """
        p = Popen('dmidecode', stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            raise DMIError('Error running dmidecode: {0}'.format(stderr.strip()))

        self.__parse_lines__(stdout.splitlines())

    def __parse_lines__(self, lines):
        """Iterator to yield parsed lines

        """

        table = None
        handle = None
        group = None
        prop = None

        for line in lines:
            if line.strip() == '':
                continue

            m = RE_VERSION.match(line)
            if m and self.version is None:
                self.version = m.groupdict()['version']
                continue

            m = RE_TABLE_START.match(line)
            if m:
                table = DMITable(address=m.groupdict()['address'])
                self.tables.append(table)
                handle = None
                group = None
                prop = None
                continue

            m = RE_HANDLE_START.match(line)
            if m and table:
                handle = DMIHandle(table, **m.groupdict())
                table.add_handle(handle)
                group = None
                prop = None
                continue

            if line.startswith('\t'):
                if group is None:
                    raise DMIError('Property outside of a group')

                if line.count('\t') == 1:
                    try:
                        prop = group.add_property(*line.lstrip('\t').split(': ' , 1))
                    except:
                        prop = group.add_property(line.lstrip('\t'))

                elif line.count('\t') == 2:
                    if prop is None:
                        raise DMIError('Option outside of a property')
                    prop.add_option(line.lstrip('\t'))

                else:
                    raise DMIError('Error parsing line {0}'.format(line))

                continue

            if handle is not None:
                group = handle.add_group(line.strip())
                continue

            else:
                self.flags.append(line.strip().rstrip('.'))

    def as_dict(self):
        """Return DMI data as dictionary

        """
        return {
            'version': self.version,
            'flags': self.flags,
            'tables': [table.as_dict() for table in self.tables]
        }

    def to_json(self):
        """Return DMI data as JSON

        """
        return json.dumps(self.as_dict(), indent=2)

    def find_groups(self, group_name):
        """Find groups by name

        """
        groups = []
        for table in self.tables:
            for handle in table.handles:
                for group in handle.groups:
                    if group.name == group_name:
                        groups.append(group)
        return groups

    def find_properties(self, group_name, property_name):
        """Find properties by group and name

        """
        properties = []
        for group in self.find_groups(group_name):
            for prop in group.properties:
                if prop.name == property_name:
                    properties.append(prop)
        return properties
