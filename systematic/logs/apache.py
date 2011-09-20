#!/usr/bin/env python 
"""
Parser for apache access logs
"""

import re,time,logging

from seine.address import IPv4Address,IPv6Address
from systematic.logs.logfile import LogFile,LogEntry,LogError

# Default regexp to match apache common access log format
re_accesslogs = [
    re.compile('^%s$' % '\s*'.join([
        '(?P<client>[^\s]*)',
        '-',
        '-',
        '\[(?P<date>[A-Za-z0-9/ :+-]+)\]',
        '"(?P<request>[^"]+)"',
        '(?P<responsecode>[0-9]+)',
        '(?P<octets>[0-9-]+)',
        '"(?P<flag2>.*)"',
        '"(?P<useragent>.*)"',
    ])),
    re.compile('^%s$' % '\s*'.join([
        '(?P<client>[^\s]*)',
        '-',
        '-',
        '\[(?P<date>[A-Za-z0-9/ :+-]+)\]',
        '"(?P<request>[^"]+)"',
        '(?P<responsecode>[0-9]+)',
        '(?P<octets>[0-9-]+)',
    ])),
]

re_errorlog = re.compile('^%s$' % '\s*'.join([
        '\[(?P<date>[A-Za-z0-9/ :+-]+)\]',
        '\[(?P<code>[^\]]+)\]',
        '(?P<message>.+)',
]))

class ApacheAccessLog(LogFile):
    def __init__(self,path,start_ts=None,end_ts=None):
        LogFile.__init__(self,path,ApacheAccessLogEntry,start_ts,end_ts)

class ApacheAccessLogEntry(LogEntry):
    def __init__(self,line,path,matches=re_accesslogs):
        LogEntry.__init__(self,line,path)

        for re_match in matches:
            m = re_match.match(line)
            if m:
                self.update(m.groupdict())
                break

        if len(self.keys()) == 0:
            raise LogError('Could not parse access log line %s' % line) 

        for k in self.keys():
            if self[k] == '-':
                self[k] = None

        for name in ['client']:
            if self[name] is None:
                continue
            try:
                self[name] = IPv4Address(self[name])
            except ValueError:
                try:
                    self[name] = IPv6Address(self[name])
                except ValueError:
                    pass

        for name in ['octets','responsecode']:
            if self[name] is None:
                continue
            try:
                self[name] = int(self[name])
            except ValueError:
                raise LogError('Could not parse %s value %s' % (name,self[name]))

        try:
            v = self['date']
            dateval = v[:v.rindex(' ')]
            self['timezone'] = v[v.rindex(' '):].lstrip()
            self['date'] = time.strptime(dateval,'%d/%b/%Y:%H:%M:%S')
        except ValueError:
            raise LogError('Error parsing date: %s' % self['date'])

class ApacheErrorLog(LogFile):
    def __init__(self,path,start_ts=None,end_ts=None):
        LogFile.__init__(self,path,ApacheErrorLogEntry,start_ts,end_ts)

class ApacheErrorLogEntry(LogEntry):
    def __init__(self,line,path,matches=re_accesslogs):
        LogEntry.__init__(self,line,path)

        m = re_errorlog.match(line)
        if not m:
            raise LogError('Could not parse error log line %s' % line)
        self.update(m.groupdict())

        try:
            dateval = self['date']
            self['date'] = time.strptime(dateval,'%a %b %d %H:%M:%S %Y')
        except ValueError:
            raise LogError('Error parsing date: %s' % self['date'])

if __name__ == '__main__':
    import sys
    #al = ApacheAccessLog(sys.argv[1])
    al = ApacheErrorLog(sys.argv[1])
    while True:
        try:
            l = al.next() #lambda e: e['client'].ipaddress=='10.3.10.23')
        except StopIteration:
            break
        print l.items()

