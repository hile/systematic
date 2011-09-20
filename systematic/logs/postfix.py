#!/usr/bin/env python 
"""
Parser for postfix SMTP logs
"""

import re,time,logging

from seine.address import IPv4Address,IPv6Address
from systematic.logs.logfile import LogFile,LogEntry,LogError
from systematic.logs.syslog import SyslogFile,SyslogEntry

re_errorlog = re.compile('^%s$' % '\s*'.join([
        '\[(?P<date>[A-Za-z0-9/ :+-]+)\]',
        '\[(?P<code>[^\]]+)\]',
        '(?P<message>.+)',
]))

# Regular expressions to match various message types in the log for postfix
re_msgid_msg = re.compile('^(?P<msgid>[A-Z0-9]{9,9}): (?P<flags>.*)$')
re_noqueue_msg = re.compile('^NOQUEUE: (?P<code>[a-z0-9]+): RCPT from (?P<source>[^\[]+)\[(?P<address>[^\]]+)\]: (?P<response>.*); (?P<flags>.*)$')
re_table_msg = re.compile('^table (?P<db>[^\s]+) (?P<event>.*)$')
re_dbfile_msg = re.compile('^warning: database (?P<db>[^\s]+) is older than source file (?P<source>.*)$')
re_warning_msg = re.compile('^warning: (?P<message>.*)$')
re_statistics_msg = re.compile('^statistics: (?P<message>.*)$')
re_connection_error_msg = re.compile('^(?P<state>.*) after (?P<code>[A-Z-]+) from (?P<source>[^\[]+)\[(?P<address>[^\]]+)\]$')
re_tls_setup_msg = re.compile('^setting up TLS connection from (?P<source>[^\[]+)\[(?P<address>[^\]]+)\]$')
re_tls_info_msg = re.compile('^Anonymous TLS connection established from (?P<source>[^\[]+)\[(?P<address>[^\]]+)\]: (?P<info>.*)$')
re_connect_to_msg = re.compile('^connect to (?P<source>[^\[]+)\[(?P<address>[^\]]+)\]:(?P<port>[0-9]+): (?P<error>.*)$')
re_connect_from_msg = re.compile('^connect from (?P<source>[^\[]+)\[(?P<address>[^\]]+)\]$')
re_disconnect_from_msg = re.compile('^disconnect from (?P<source>[^\[]+)\[(?P<address>[^\]]+)\]$')
re_warn_hostname_verify = re.compile('^(?P<address>[0-9af.:]+): hostname (?P<hostname>.*) verification failed: (?P<error>.*)$')
re_warn_no_valid_mx = re.compile('^no MX host for (?P<domain>[^\s]+) has a valid address record$')
re_warn_addr_not_listed = re.compile('^(?P<address>[^:]+): address not listed for hostname (?P<hostname>.*)$')

class PostfixSMTPLog(SyslogFile):
    def __init__(self,path,start_ts=None,end_ts=None):
        SyslogFile.__init__(self,path,start_ts,end_ts)
        self.logclass = PostFixSMTPLogEntry

    def next(self):
        while True:
            try:
                entry = PostFixSMTPLogEntry(LogFile.next(self).line,self.path)
                if entry.program == 'postfix':
                    return entry
            except StopIteration:
                break
        raise StopIteration

class PostFixSMTPLogEntry(SyslogEntry):
    def __init__(self,line,path):
        SyslogEntry.__init__(self,line,path)
        try:
            (program,module) = self.program.split('/',1)
            self['program'] = 'postfix'
            self['module'] = module
        except ValueError:
            pass

        self.msgtype = None
        m = re_msgid_msg.match(self.message)
        if m:
            self.msgtype = 'delivery'
            self.update(m.groupdict())

            flags = self['flags']
            self['flags'] = {}
            while len(flags)>0:
                try:
                    v = flags[:flags.index(', ')]
                except ValueError:
                    v = flags
                    flags = ''
                flags = flags[len(v)+2:]

                while v.count('(')>v.count(')'):
                    try:
                        s = flags[:flags.index(')')+1]
                        v += s
                        flags = flags[len(s):]
                    except ValueError:
                        raise LogError('Error parsing %s %s' % (v,flags))
                    if len(flags)==0:
                        break
                try:
                    (key,value) = v.split('=',1)
                    self['flags'][key] = value
                except ValueError:
                    pass

            if self['flags'].has_key('from'):
                if self['flags']['from'] != '<>':
                    self['sender'] = self['flags']['from']
                del(self['flags']['from'])
            if self['flags'].has_key('to'):
                if self['flags']['to'] != '<>':
                    self['recipient'] = self['flags']['to']
                del(self['flags']['to'])
            if not self.has_key('sender'):
                self['sender'] = None
            if not self.has_key('recipient'):
                self['recipient'] = None

            if self['flags'].has_key('status'):
                (code,msg) = self['flags']['status'].split(None,1)
                self['status'] = code
                self['status_message'] = msg
            else:
                self['status'] = None
                self['status_message'] = ''

            return

        m = re_noqueue_msg.match(self.message)
        if m:
            self.msgtype = 'noqueue'
            self.update(m.groupdict())
            if self.has_key('flags'):
                self['flags'] = dict([k.split('=',1) for k in self['flags'].split()])
            return

        m = re_tls_setup_msg.match(self.message)
        if m:
            self.msgtype = 'tls_init'
            self.update(m.groupdict())
            return

        m = re_tls_info_msg.match(self.message)
        if m:
            self.msgtype = 'tls_info'
            self.update(m.groupdict())
            return

        m = re_connection_error_msg.match(self.message)
        if m:
            self.msgtype = 'connection_error'
            self.update(m.groupdict())
            return

        m = re_connect_to_msg.match(self.message)
        if m:
            self.msgtype = 'connect_to'
            self.update(m.groupdict())
            return

        m = re_connect_from_msg.match(self.message)
        if m:
            self.msgtype = 'connect_from'
            self.update(m.groupdict())
            return

        m = re_disconnect_from_msg.match(self.message)
        if m:
            self.msgtype = 'disconnect_from'
            self.update(m.groupdict())
            return

        m = re_table_msg.match(self.message)
        if m:
            self.msgtype = 'table'
            self.update(m.groupdict())
            return 

        m = re_statistics_msg.match(self.message)
        if m:
            self.msgtype = 'statistics'
            self.update(m.groupdict())
            return 

        m = re_dbfile_msg.match(self.message)
        if m:
            self.msgtype = 'database'
            self.update(m.groupdict())
            return 

        m = re_warning_msg.match(self.message)
        if m:
            self.msgtype = 'warning'
            self.warning_type = None
            self.update(m.groupdict())

            m = re_warn_hostname_verify.match(self.message)
            if m:
                self.warning_type = 'hostname_verification'
                self.update(m.groupdict())
                return 

            m = re_warn_no_valid_mx.match(self.message)
            if m:
                self.warning_type = 'no_valid_mx'
                self.update(m.groupdict())
                return

            m = re_warn_addr_not_listed.match(self.message)
            if m:
                self.warning_type = 'no_matching_address'
                self.update(m.groupdict())
                return
            return

if __name__ == '__main__':
    import sys
    al = PostfixSMTPLog(sys.argv[1])

    while True:
        try:
            l = al.next() #lambda e: e['client'].ipaddress=='10.3.10.23')
        except StopIteration:
            break
        print l.msgtype,l.items()

