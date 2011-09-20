#!/usr/bin/env python 
"""
Parser for squid access and cache logs
"""

import re,time,logging

from seine.address import IPv4Address,IPv6Address
from systematic.logs.logfile import LogFile,LogEntry,LogError

re_accesslog = re.compile('^%s$' % '\s+'.join([
    '(?P<timestamp>[0-9.]+)',
    '(?P<duration>\d+)',
    '(?P<client>[0-9a-f.:]+)',
    '(?P<result>[^/]+)/(?P<status_code>\d+)',
    '(?P<bytes>\d+)',
    '(?P<request_method>[A-Z0-9_]+)',
    '(?P<url>[^\s]+)',
    '(?P<ident>[^\s]+)',
    '(?P<cache_code>[^/]+)/(?P<target_address>[^\s]+)',
    '(?P<content_type>[^\s]+)'
]))

class SquidAccessLog(LogFile):
    def __init__(self,path,start_ts=None,end_ts=None):
        LogFile.__init__(self,path,SquidAccessLogEntry,start_ts,end_ts)

class SquidAccessLogEntry(LogEntry):
    def __init__(self,line,path):
        LogEntry.__init__(self,line,path)

        m = re_accesslog.match(line)
        if not m:
            raise LogError('Could not parse access log line %s' % line) 
        self.update(m.groupdict())

        for k in self.keys():
            if self[k] == '-':
                self[k] = None

        for name in ['client','target_address']:
            if self[name] is None:
                continue
            try:
                self[name] = IPv4Address(self[name])
            except ValueError:
                try:
                    self[name] = IPv6Address(self[name])
                except ValueError:
                    pass

        for name in ['bytes','status_code','duration']:
            try:
                self[name] = int(self[name])
            except ValueError:
                raise LogError('Could not parse %s value %s' % (name,self[name]))

        self['time'] = time.localtime(int(float(self['timestamp'])))

if __name__ == '__main__':
    import sys
    sal = SquidAccessLog(sys.argv[1])
    while True:
        try:
            l = sal.next(lambda e: e['client'].ipaddress=='10.3.10.23')
        except StopIteration:
            break
        print l

