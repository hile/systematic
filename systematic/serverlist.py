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

        if not os.path.isfile(path):
            raise ValueError('No such file: %s' % path)
        try:
            config  = ConfigObj(path)
        except ValueError,emsg:
            raise ValueError('Error parsing %s: %s' % (path,emsg))
        for k in config.keys():
            self[k] = OperatingSystemGroup(k,config[k])

class OperatingSystemGroup(list):
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
            self.connect_command = ['ssh','-qt','SERVER']

        try:
            self.command_separator = opts['command_separator']
        except KeyError:
            self.command_separator = ' && '

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

class ServerConfig(object):
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
        if type(command) != list:
            command = [command]
        cmd = self.connect_command + command
        p = Popen(cmd,stdout=PIPE,stderr=PIPE)
        (stdout,stderr) = p.communicate()
        return p.returncode,stdout.rstrip('\n'),stderr.rstrip('\n')

    def shell(self,command):
        if type(command) != list:
            command = [command]
        cmd = self.connect_command + command
        p = Popen(cmd,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr)
        p.wait()
        return p.returncode

    def update(self):
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

