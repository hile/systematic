#!/usr/bin/env python
"""
Configuration classes to enumerate servers in an organization, and to run
basic update, non-interactive and interactive shell commands on the servers.

Designed for usage over ssh, could work with other protocols I guess at 
least for interactive sessions (start VNC etc).
"""

import sys,os,logging
from subprocess import Popen,PIPE
from configobj import ConfigObj

DEFAULT_COMMAND_SEPARATOR = ' && '
DEFAULT_CONNECT_COMMAND = ['ssh','-qt','SERVER']

class OrganizationServers(dict):
    """
    Parser for configuration file describing organization's servers and
    their operating systems.
    """
    def __init__(self,path):
        dict.__init__(self)
        self.log = logging.getLogger('modules')
        self.path = path

        if not os.path.isfile(self.path):
            return
        try:
            config  = ConfigObj(self.path)
        except ValueError,emsg:
            raise ValueError('Error parsing %s: %s' % (self.path,emsg))
        for k in config.keys():
            self[k] = OperatingSystemGroup(k,config[k])

    def save(self):
        config = ConfigObj()
        for name,group in self.items():
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
    def __init__(self,name,opts):
        list.__init__(self)
        self.modified = False
        self.log = logging.getLogger('modules')
        self.name = name
        self.description = name
        self.connect_command = DEFAULT_CONNECT_COMMAND
        self.command_separator = DEFAULT_COMMAND_SEPARATOR
        self.update_commands = None

        if opts.has_key('description'):
            self.description = opts['description']
        if opts.has_key('connect'):
            self.connect_command = opts['connect']
        if opts.has_key('command_separator'):
            self.command_separator = opts['command_separator']
        if opts.has_key('commands'):
            self.update_commands = opts['commands']
            if isinstance(self.update_commands,basestring):
                self.update_commands = [self.update_commands]
        if opts.has_key('servers'):
            for server in opts['servers']:
                self.append(ServerConfig(self,server))

    def __repr__(self):
        return '%s: %s (%d servers)' % (
            self.name,self.description,len(self)
        )

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
    def __init__(self,os,name):
        self.log = logging.getLogger('modules')
        self.os = os
        self.name = name
        self.connect_command = [
            x=='SERVER' and name or x for x in os.connect_command
        ]

    def __repr__(self):
        return '%s (OS: %s, Update: %s)' % (
            self.name,
            self.os.description,
            self.os.update_commands is not None and 'Yes' or 'No'
        )

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

