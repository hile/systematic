#!/usr/bin/env python
"""
Configuration classes to enumerate servers in an organization & to run
basic update, non-interactive and interactive shell commands on the servers.

Designed for usage over ssh, could work with other protocols I guess at
least for interactive sessions (start VNC etc).
"""

import sys,os
from subprocess import Popen,PIPE
from configobj import ConfigObj

from systematic.log import Logger,LoggerError

DEFAULT_COMMAND_SEPARATOR = ' && '
DEFAULT_CONNECT_COMMAND = ['ssh','-qt','SERVER']

SERVERINFO_FIELDS = ['hostname','description']

class OrganizationServers(dict):
    """
    Parser for configuration file describing organization's servers and
    their operating systems.
    """
    def __init__(self,path):
        self.log = Logger('servers').default_stream
        self.path = path

        if not os.path.isfile(self.path):
            return
        try:
            config  = ConfigObj(self.path)
        except ValueError,emsg:
            raise ValueError('Error parsing %s: %s' % (self.path,emsg))

        self.serverinfo = {}
        for k in config.keys():
            if config[k].has_key('servers'):
                self[k] = OperatingSystemGroup(k,config[k])
            else:
                self.serverinfo[k] = config[k]

        for group in self.values():
            for server in group:
                if not server.name in self.serverinfo.keys():
                    continue
                info = self.serverinfo[server.name]
                for k in SERVERINFO_FIELDS:
                    if k not in info.keys():
                        continue
                    v = info[k]
                    if isinstance(v,list):
                        v = ', '.join(v)
                    setattr(server,k,v)

    def save(self):
        config = ConfigObj()
        for name,group in self.items():
            if len(group)==0:
                continue
            config[name] = {
                'commands': group.update_commands,
                'servers': [s.name for s in group],
            }
            if group.description != group.name:
                config[name]['description'] = group.description
            if group.connect_command!=DEFAULT_CONNECT_COMMAND:
                config[name]['connect'] = group.connect_command
            if group.command_separator!=DEFAULT_COMMAND_SEPARATOR:
                config[name]['command_separator'] = group.command_separator

        self.log.debug('Saving configuration to %s' % self.path)
        config.write(outfile=open(self.path,'w'))

class OperatingSystemGroup(list):
    """
    Group of operating systems in configuration file
    """
    def __init__(self,name,opts={}):
        self.log = Logger('servers').default_stream
        self.modified = False
        self.name = name
        self.description = name
        self.connect_command = DEFAULT_CONNECT_COMMAND
        self.command_separator = DEFAULT_COMMAND_SEPARATOR
        self.update_commands = None

        if opts.has_key('description'):
            self.description = opts['description']
        if opts.has_key('connect'):
            self.connect_command = opts['connect']
            if isinstance(self.connect_command,basestring):
                self.connect_command = self.connect_command.split()
        if opts.has_key('command_separator'):
            self.command_separator = opts['command_separator']
        if opts.has_key('commands'):
            self.update_commands = opts['commands']
            if isinstance(self.update_commands,basestring):
                self.update_commands = [self.update_commands]
        if opts.has_key('servers'):
            servers = opts['servers']
            if not isinstance(servers,list):
                servers = [servers]
            self.extend(ServerConfig(self,s) for s in servers)

    def __repr__(self):
        return '%s: %s (%d servers)' % (self.name,self.description,len(self))

    def setCommandSeparator(self,separator):
        if self.command_separator != separator:
            self.log.debug('Modified command separator for %s' % self.name)
            self.command_separator = separator
            self.modified = True

    def setConnectCommand(self,command):
        if not isinstance(command,list):
            raise ValueError('Connect command must be a list')
        if self.connect_command != command:
            self.log.debug('Modified connect commands for %s' % self.name)
            self.connect_command = command
            self.modified = True

    def setDescription(self,description):
        if self.description != description:
            self.log.debug('Modified description for %s' % self.name)
            self.description = description
            self.modified = True

    def setUpdateCommands(self,update_commands):
        if not isinstance(update_commands,list):
            raise ValueError('Update commands value not a list')
        if self.update_commands!=update_commands:
            self.log.debug('Modified update commands for %s' % self.name)
            self.update_commands = update_commands
            self.modified = True

    def addServer(self,name):
        try:
            filter(lambda s: s.name==name, self)[0]
            self.log.debug('Error adding: server already in group: %s' % name)
        except IndexError:
            self.log.debug('Added server to %s' % self.name)
            self.append(ServerConfig(self,name))
            self.modified = True

    def removeServer(self,name):
        try:
            server = filter(lambda s: s.name==name, self)[0]
            self.log.debug('Removed server from %s' % self.name)
            self.remove(server)
            self.modified = True
        except IndexError:
            self.log.debug('Error removing: server not in group: %s' % name)

class ServerConfig(object):
    """
    Configuration for one server
    """
    def __init__(self,os,name,description=None):
        self.log = Logger('servers').default_stream
        self.os = os
        self.name = name
        self.description = description
        self.connect_command = [x=='SERVER' and name or x for x in os.connect_command]

    def __repr__(self):
        if self.description is not None:
            return '%s (%s)' % (self.name,self.description)
        else:
            return '%s' % self.name

    def check_output(self,command):
        """
        Wrapper to check output of a command
        """
        if type(command) != list:
            command = [command]
        cmd = self.connect_command + command
        p = Popen(cmd,stdout=PIPE,stderr=PIPE)
        (stdout,stderr) = p.communicate()
        return p.returncode,stdout.rstrip('\n'),stderr.rstrip('\n')

    def shell(self,command):
        """
        Wrapper to run interactive shell on the host
        """
        if type(command) != list:
            command = [command]
        cmd = self.connect_command + command
        p = Popen(cmd,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr)
        p.wait()
        return p.returncode

    def update(self):
        """
        Wrapper to call correct update commands for this host
        """
        if self.os.update_commands is None:
            self.log.debug('No update commands for OS %s' % self.os.name)
            return
        self.log.debug("Running: %s '%s'" % (
            ' '.join(self.connect_command),
            self.os.command_separator.join(self.os.update_commands)
        ))
        cmd = self.connect_command + [
            self.os.command_separator.join(self.os.update_commands)
        ]
        p = Popen(cmd,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr)
        p.wait()
        return p.returncode

