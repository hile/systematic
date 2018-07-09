"""
Configuration classes to enumerate servers in an organization & to run
basic update, non-interactive and interactive shell commands on the servers.

Designed for usage over ssh, could work with other protocols I guess at
least for interactive sessions (start VNC etc).
"""

import sys
import os
from subprocess import Popen, PIPE
from configobj import ConfigObj

from systematic.log import Logger

DEFAULT_COMMAND_SEPARATOR = ' && '
DEFAULT_CONNECT_COMMAND = ['ssh', '-qt', 'SERVER']

SERVERINFO_FIELDS = (
    'hostname',
    'description',
)


class Server(object):
    """
    Configuration for one server
    """
    def __init__(self, osgroup, name, description=None):
        self.log = Logger().default_stream
        self.osgroup = osgroup
        self.name = name
        self.description = description

    def __repr__(self):
        if self.description is not None:
            return '{0} ({1})'.format(self.name, self.description)
        else:
            return '{0}'.format(self.name)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return self.name == other.name

    def __ne__(self, other):
        if isinstance(other, str):
            return self.name != other
        return self.name != other.name

    def __gt__(self, other):
        if isinstance(other, str):
            return self.name > other
        return self.name > other.name

    def __lt__(self, other):
        if isinstance(other, str):
            return self.name < other
        return self.name < other.name

    def __ge__(self, other):
        if isinstance(other, str):
            return self.name >= other
        return self.name >= other.name

    def __le__(self, other):
        if isinstance(other, str):
            return self.name <= other
        return self.name <= other.name

    @property
    def connect_command(self):
        return [x == 'SERVER' and self.name or x for x in self.osgroup.connect_command]

    def check_output(self, command):
        """
        Wrapper to execute and check output of a command without
        interactive console actions

        Splits string automatically to words so pass a list if you
        need to escape stuff properly.
        """
        if not isinstance(command, list):
            command = [command]

        cmd = self.connect_command + command
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = p.communicate()
        return p.returncode, stdout.rstrip('\n'), stderr.rstrip('\n')

    def shell(self, command):
        """
        Wrapper to run interactive shell command on the host, using
        current terminal for stdin, stdout and stderr

        Splits string automatically to words so pass a list if you
        need to escape stuff properly.

        Returns command return code
        """
        if not isinstance(command, list):
            command = [command]

        cmd = self.connect_command + command
        p = Popen(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()
        return p.returncode

    def update(self):
        """
        Wrapper to call correct update commands for this host
        """
        if not self.osgroup.update_commands:
            self.log.debug('No update commands for OS {0}'.format(self.osgroup.name))
            return

        self.log.debug("Running: {0} '{1}'".format(
            ' '.join(self.connect_command),
            self.osgroup.command_separator.join(self.osgroup.update_commands)
        ))

        cmd = self.connect_command + [
            self.osgroup.command_separator.join(self.osgroup.update_commands)
        ]
        p = Popen(cmd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()
        return p.returncode

    def remove(self):
        """Remove from configuration

        Remove this server from configuration

        """
        return self.osgroup.remove_server(self)


class OperatingSystemGroup(object):
    """
    Group of operating systems in configuration file
    """

    def __init__(self, config, name, **kwargs):
        self.log = Logger().default_stream
        self.name = name
        self.description = name
        self.connect_command = DEFAULT_CONNECT_COMMAND
        self.command_separator = DEFAULT_COMMAND_SEPARATOR
        self.update_commands = []
        self.servers = []

        for k in ('description', 'command_separator'):
            if k in kwargs:
                setattr(self, k, kwargs[k])

        if 'connect' in kwargs:
            self.connect_command = kwargs['connect']

        if 'commands' in kwargs:
            self.update_commands = kwargs['commands']

        if 'servers' in kwargs:
            names = kwargs['servers']
            if not isinstance(names, list):
                names = [names]

            for name in names:
                self.servers.append(Server(self, name))

        self.modified = False

    def __repr__(self):
        return '{0}: {1} ({2:d} servers)'.format(self.name, self.description, len(self.servers))

    @property
    def command_separator(self):
        return self._command_separator

    @command_separator.setter
    def command_separator(self, value):
        self._command_separator = value
        self.modified = True

    @property
    def connect_command(self):
        return self._connect_command

    @connect_command.setter
    def connect_command(self, value):
        if isinstance(value, str):
            value = value.split()
        self._connect_command = value
        self.modified = True

    @property
    def update_command(self):
        return self._update_commands

    @update_command.setter
    def update_commands(self, value):
        if isinstance(value, str):
            value = [value]
        self._update_commands = value
        self.modified = True

    @property
    def descripion(self):
        return self._descripion

    @descripion.setter
    def descripion(self, value):
        self._descripion = value
        self.modified = True

    def add_server(self, name):
        if name in [s.name for s in self.servers]:
            self.log.debug('Error adding: server already in group: {0}'.format(name))
            return

        self.servers.append(Server(self, name))
        self.modified = True

    def remove_server(self, name):
        try:
            server = [s for s in self.servers if s.name == name][0]
            self.servers.remove(server)
            self.modified = True
        except IndexError:
            self.log.debug('Error removing: server not in group: {0}'.format(name))
            return


class ServerConfigFile(object):
    """
    Parser for configuration file describing servers and their
    operating systems.
    """
    def __init__(self, path):
        self.operating_systems = []
        self.servers = []
        self.path = path
        self.log = Logger().default_stream

        if os.path.isfile(self.path):
            self.load()

    @property
    def osnames(self):
        return [x.name for x in self.operating_systems]

    def load(self):
        self.operating_systems = []
        self.servers = []

        try:
            config = ConfigObj(self.path)
        except ValueError as e:
            raise ValueError('Error parsing {0}: {1}'.format(self.path, e))

        osgroup = None
        for key, section in config.items():
            if 'commands' in section:
                if key in self.servers:
                    raise ValueError('Duplicate OS group name: {0}'.format(key))
                osgroup = OperatingSystemGroup(self, key, **section)
                self.operating_systems.append(osgroup)
                self.servers.extend(osgroup.servers)
            else:
                if osgroup is None:
                    raise ValueError('Server in configuration file but no OS group defined yet')
                self.servers.append(Server(osgroup, section))

        return

    def save(self):
        config = ConfigObj()

        for osgroup in self.operating_systems:
            section = {
                'commands': osgroup.update_commands,
            }

            if osgroup.description is not None and osgroup.description != '':
                section['description'] = osgroup.description

            if osgroup.servers:
                section['servers'] = osgroup.servers

            if osgroup.connect_command != DEFAULT_CONNECT_COMMAND:
                section['connect'] = osgroup.connect_command

            if osgroup.command_separator != DEFAULT_COMMAND_SEPARATOR:
                section['command_separator'] = osgroup.command_separator

            config[osgroup.name] = section
            for server in osgroup.servers:
                if server.description:
                    config[server.name] = {
                        'description': server.description
                    }

        self.log.debug('Saving configuration to {0}'.format(self.path))
        config.write(outfile=open(self.path, 'w'))

    def match_os(self, name):
        for operating_system in self.operating_systems:
            if operating_system.name == name:
                return operating_system

        raise ValueError('Unknown OS: {0}'.format(name))
