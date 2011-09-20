#!/usr/bin/env python
"""
Generic parser for syslog log files
"""

import os,gzip,re,sys,time
from systematic.logs.logfile import LogFile,LogEntry,LogError

SYSLOG_FIELD_ORDER = ['timestamp','host','program','message']

TIMESTAMP_FORMATS = [
    '%Y %b %d %H:%M:%S'
]

re_syslogline = re.compile(r'^%s\s*$' % '\s*'.join([
   '(?P<time>[^\s]*\s*[0-9]*\s*[0-9:]*)',
   '(?P<host>[^\s]*)',
   '(?P<program>[^\s]*)',
   '(?P<message>.*)',
  ])
)

class SyslogFile(LogFile):
    def __init__(self,path,start_ts=None,end_ts=None):
        LogFile.__init__(self,path,SyslogEntry,start_ts,end_ts)

class SyslogEntry(LogEntry):
    def __init__(self,line,path):
        LogEntry.__init__(self,line,path)

        m = re_syslogline.match(line)
        if not m:
            raise LogError('Could not parse log line: %s' % line)
        self.update(m.groupdict())

        m = re.match('(?P<program>[^\[]*)\[(?P<pid>[0-9]*)\].*',self['program'])
        if m:
            self['program'] = m.group(1)
            self['pid'] = m.group(2)
        else:
            self['pid'] = None

        try:
            year = time.localtime(os.stat(path).st_mtime).tm_year
            timevalue = '%s %s' % (year,self['time'].rstrip(':'))
        except KeyError:
            raise LogError('No time value parsed for log line')

        self['timestamp'] = None
        for fmt in TIMESTAMP_FORMATS:
            try:
                self['time'] = time.strptime(timevalue,fmt)
                self['timestamp'] = time.mktime(self['time'])
            except ValueError:
                continue
        if self['timestamp'] == None:
            raise LogError('Invalid time value: %s' % timevalue)

        for k in ['timestamp','pid']:
            if not self.has_key(k): 
                continue
            try:
                self[k] = int(self[k])
            except ValueError:
                raise LogError('Invalid value for field %s: %s' % (k,self[k]))
            except TypeError:
                pass

    def __str__(self):
        return '%s %s' % (
            self.date,
            ' '.join(['%s' % self[k] for k in SYSLOG_FIELD_ORDER[1:]])
        )

if __name__ == '__main__':
    if len(sys.argv)>2:
        sl = SyslogFile(path=sys.argv[1],start_ts=sys.argv[2],end_ts=sys.argv[3])
    else:
        sl = SyslogFile(path=sys.argv[1])

    for l in sl:
        print l.message

