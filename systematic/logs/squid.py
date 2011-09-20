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

re_cachelog = re.compile('^(?P<date>[0-9/:\s]+)\|\s+(?P<message>.+)$')
re_clienttryparse = re.compile('^FD\s+(?P<fd>[0-9]+)\s+\((?P<client>[0-9.:]+)\)\s+(?P<error>.*)$')

class SquidCacheLog(LogFile):
    def __init__(self,path,start_ts=None,end_ts=None):
        LogFile.__init__(self,path,SquidCacheLogEntry,start_ts,end_ts)

class SquidCacheLogEntry(LogEntry):
    def __init__(self,line,path):
        LogEntry.__init__(self,line,path)
        m = re_cachelog.match(line)
        if not m:
            raise LogError('Could not parse cache log line %s' % line) 
        self.update(m.groupdict())

        try:
            self['date'] = time.strptime(self['date'],'%Y/%m/%d %H:%M:%S')
        except ValueError:
            raise LogError('Error parsing date %s' % self['date'])

        try:
            (code,msg) = self['message'].split(':',1)
            self['code'] = code
            self['message'] = msg.lstrip()
        except ValueError:
            self['code'] = 'progress'

        if self.code == 'clientTryParseRequest':
            m = re_clienttryparse.match(self.message)
            if not m:
                raise LogError(
                    'Error parsing clientTryParseRequest line: %s' % self.message
                )
            self.update(m.groupdict())
            try:
                v = self['client']
                self['address'] = IPv4Address(v[:v.rindex(':')])
                self['port'] = int(v[v.rindex(':')+1:])
            except ValueError:
                raise LogError(
                    'Error parsing clientTryParseRequest client: %s' % self['client']
                )
                

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
    log = SquidCacheLog(sys.argv[1])
    for address in sorted(list(set([l.address for l in log.filter(
            lambda e: e['code'] in ['clientTryParseRequest']
        )]))):
        print address.ipaddress
        #print l.code,l.address.ipaddress,l.port

