#!/usr/bin/env python 
"""
Parser for dovecot server logs
"""

import re

from systematic.logs.logfile import LogFile
from systematic.logs.syslog import SyslogFile,SyslogEntry

re_system = re.compile('^dovecot: (?P<message>.*)$')
re_login = re.compile('^(?P<service>[a-z0-9]+)-login: Login: user=<(?P<username>[^>]+)>, method=(?P<method>[^,]+), rip=(?P<client>[0-9a-f.:]+), lip=(?P<local>[0-9a-f.:]+)(?P<flags>.*)$')
re_handshake_aborted = re.compile('^(?P<service>[a-z0-9]+)-login: Disconnected: (?P<reason>.*) \(no auth attempts\): rip=(?P<client>[0-9a-f.:]+), lip=(?P<local>[0-9a-f.:]+)(?P<state>.*)$')
re_login_aborted = re.compile('^(?P<service>[a-z0-9]+)-login: Aborted login \(no auth attempts\): rip=(?P<client>[0-9a-f.:]+), lip=(?P<local>[0-9a-f.:]+)(?P<flags>.*)$')
re_connection_closed = re.compile('^(?P<service>[A-Z0-9]+)\((?P<username>[^\)]+)\): Connection closed bytes=(?P<bytes_in>[0-9]+)/(?P<bytes_out>[0-9]+)$')
re_disconnect_user = re.compile('^(?P<service>[A-Z0-9]+)\((?P<username>[^\)]+)\): Disconnected(?P<details>.*)$')

class DovecotLog(SyslogFile):
    """
    Parser for dovecot mail server log messages.
    """
    def __init__(self,path,start_ts=None,end_ts=None):
        SyslogFile.__init__(self,path,start_ts,end_ts)
        self.logclass = DovecotLogEntry

    #noinspection PyMethodOverriding
    def next(self):
        while True:
            try:
                entry = DovecotLogEntry(LogFile.next(self).line,self.path)
                if entry.program == 'dovecot':
                    return entry
            except StopIteration:
                break
        raise StopIteration

class DovecotLogEntry(SyslogEntry):
    def __init__(self,line,path):
        SyslogEntry.__init__(self,line,path)
        try:
            (program,module) = self.program.split(':',1)
            self['program'] = program
            self['module'] = module
        except ValueError:
            pass

        m = re_login.match(self.message)
        if m:
            self['module'] = 'login'
            self.update(m.groupdict())
            flags = self['flags'].lstrip(', ')
            self['flags'] = flags.split()
            return

        m = re_handshake_aborted.match(self.message)
        if m:
            self['module'] = 'handshake_aborted'
            self.update(m.groupdict())
            self['state'] = self['state'].lstrip()
            return

        m = re_login_aborted.match(self.message)
        if m:
            self['module'] = 'login_aborted'
            self.update(m.groupdict())
            flags = self['flags'].lstrip(', ')
            self['flags'] = flags.split()
            return

        m = re_connection_closed.match(self.message)
        if m:
            self['module'] = 'connection_closed'
            self.update(m.groupdict())
            for k in ['bytes_in','bytes_out']:
                self[k] = int(self[k])
            return

        m = re_disconnect_user.match(self.message)
        if m:
            self['module'] = 'disconnect_user'
            self.update(m.groupdict())
            self['details'] = self['details'].lstrip()
            return

        m = re_system.match(self.message)
        if m:
            self['module'] = 'system'
            self.update(m.groupdict())
            return

if __name__ == '__main__':
    import sys
    dl = DovecotLog(sys.argv[1])

    while True:
        try:
            l = dl.next() #lambda e: e['client'].ipaddress=='10.3.10.23')
        except StopIteration:
            break
        if l.module == '':
            print l.message
            continue
        for k,v in l.items():
            print k,v

