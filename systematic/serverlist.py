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
        for k,v in config.items():
            print k,v
        config.write(outfile=open(self.path,'w'))

DEFAULT_COMMAND_SEPARATOR = ' && '
DEFAULT_CONNECT_COMMAND = ['ssh','-qt','SERVER']

class OperatingSystemGroup(list):
    """
    Group of operating systems in configuration file
    """
    def __init__(self,name,opts):
        list.__init__(self)
        self.log = logging.getLogger('modules')
        self.name = name
        try:
            self.description = opts['description']
        except KeyError:
            self.description = name
        try:
            self.connect_command = opts['connect']
        except KeyError:
            self.connect_command = DEFAULT_CONNECT_COMMAND

        try:
            self.command_separator = opts['command_separator']
        except KeyError:
            self.command_separator = DEFAULT_COMMAND_SEPARATOR

        try:
            self.update_commands = opts['commands']
            if not len(self.update_commands):
                self.update_commands = None
        except KeyError:
            self.update_commands = None

        try:
            self.extend(map(lambda s: ServerConfig(self,s), opts['servers']))
        except KeyError:
            pass

    def __repr__(self):
        return '%s: %s (%d servers)' % (
            self.name,self.description,len(self)
        )

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
        cmd = self.connect_command + [
            self.os.command_separator.join(self.os.update_commands)
        ]
        self.log.debug('Running: %s' % cmd)
        p = Popen(cmd,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr)
        p.wait()    
        return p.returncode

