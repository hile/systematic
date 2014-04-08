
import os
import re
from datetime import datetime, timedelta

from systematic.log import LogEntry, LogFile, LogFileError

RE_ICINGA_LOG = [
    re.compile('^\[(?P<epoch>\d+)\] (?P<category>[^:]+): (?P<message>.*)$'),
    re.compile('^\[(?P<epoch>\d+)\] (?P<message>.*)$'),
]

class IcingaLogEntry(LogEntry):
    def __init__(self, line, year, source_formats):
        line = line.strip()
        self.line = line

        self.time = None
        for parser in RE_ICINGA_LOG:
            m = parser.match(line)
            if m:
                fields = m.groupdict()
                self.time = datetime.fromtimestamp(float(fields['epoch']))
                self.category = fields.get('category', '').strip()
                self.message = fields.get('message', '').strip()
                break

        if self.time is None:
            raise LogFileError('Error parsing entry %s' % line)

    def __repr__(self):
        if self.category:
            return '%s %s %s' % (self.time, self.category, self.message)
        else:
            return '%s %s' % (self.time, self.message)

class IcingaLog(LogFile):
    lineloader = IcingaLogEntry


log = IcingaLog('~/icinga.log')

for l in log:
    print l
