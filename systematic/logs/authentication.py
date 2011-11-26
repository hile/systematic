#!/usr/bin/env python
"""
Parser for common authentication log messages
"""

import re,time,logging

from seine.address import IPv4Address,IPv6Address
from systematic.logs.logfile import LogFile,LogEntry,LogError
from systematic.logs.syslog import SyslogFile,SyslogEntry

class AuthenticationLog(SyslogFile):
    def __init__(self,path,start_ts=None,end_ts=None):
        SyslogFile.__init__(self,path,start_ts,end_ts)
        self.logclass = AuthenticationLogEntry

class AuthenticationLogEntry(SyslogEntry):
    def __init__(self,line,path):
        SyslogEntry.__init__(self,line,path)

        if self.program == 'sshd':
            self['parser'] = SshdLogMessage(self)

        elif self.program == 'su':
            self['parser'] = SudoLogMessage(self)

        elif self.program == 'sudo:':
            self['parser'] = SudoLogMessage(self)

        elif self.program.lower() == 'cron':
            self['parser'] = CronLogMessage(self)

class AuthLogMessage(dict):
    def __init__(self,entry):
        self.entry = entry
        self.message = entry.message

    def __getattr__(self,attr):
        try:
            return self.entry[attr]
        except KeyError:
            pass
        raise AttributeError

    def __str__(self):
        return self.entry.program

class SuLogMessage(AuthLogMessage):
    def __init__(self,entry):
        AuthLogMessage.__init__(self,entry)

class SudoLogMessage(AuthLogMessage):
    def __init__(self,entry):
        AuthLogMessage.__init__(self,entry)

class CronLogMessage(AuthLogMessage):
    def __init__(self,entry):
        AuthLogMessage.__init__(self,entry)

class SshdLogMessage(AuthLogMessage):
    def __init__(self,entry):
        AuthLogMessage.__init__(self,entry)

if __name__ == '__main__':
    import sys
    al = AuthenticationLog(sys.argv[1])

    while True:
        try:
            l = al.next() #lambda e: e['client'].ipaddress=='10.3.10.23')
        except StopIteration:
            break
        if l.has_key('parser'):
            continue
            print l.parser,l.message
        else:
            print l.program,l.message

