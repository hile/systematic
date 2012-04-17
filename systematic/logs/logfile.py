#!/usr/bin/env python
"""
Common classes for logfile iteration and log entry processing
"""

import os,time,gzip,logging

class LogLineTypeError(Exception):
    """
    Exception raised when log lines of unknown types are detected
    """
    def __str__(self):
        return self.args[0]

class LogError(Exception):
    """
    Exception raised for errors processing log files
    """
    def __str__(self):
        return self.args[0]

class LogFile(object):
    """
    Base class for parsing generic log file as iterator. Normally you
    want to inherit this and write a log file specific parser.
    """
    def __init__(self,filename,logclass=None,start_ts=None,end_ts=None,ignore_errors=False):
        self.log = logging.getLogger('modules')
        self.__next = 0
        self.path = filename
        self.fd = None
        self.stat = None
        self.ignore_errors = ignore_errors

        if logclass is not None:
            self.logclass = logclass
        else:
            self.logclass = LogEntry

        if start_ts is not None:
            try:
                self.start_ts = int(start_ts)
            except ValueError:
                raise LogError('Invalid timestamp range start value')
        else:
            self.start_ts = 0 
        if end_ts is not None:
            try:
                self.end_ts = int(end_ts)
            except ValueError:
                raise LogError('Invalid timestamp range end value')
        else:
            self.end_ts = None
        if start_ts is not None and end_ts is not None:
            if self.start_ts >= self.end_ts:
                raise LogError('Start timestamp must be smaller than end timestamp') 

    def __del__(self):
        if self.fd:
            self.fd.close()

    def __iter__(self):
        return self

    def open(self):
        """
        Open logfile, to be used as an iterator
        """
        if self.fd: 
            self.fd.close()
            self.fd = None
        try:
            self.fd = open(self.path,'r')
            self.stat = os.stat(self.path)
        except OSError,(ecode,emsg):
            raise LogError('Error opening %s: %s' % (self.path,emsg))
        except IOError,(ecode,emsg):
            raise LogError('Error opening %s: %s' % (self.path,emsg))

    def next(self,filter_function=None):
        """
        Return next log line from the log
        If function is given, only log messages passing filter function
        are returned.
        """
        entry = None
        if not self.fd:
            try:
                if self.path.endswith('gz'):
                    self.fd = gzip.GzipFile(self.path)
                else:
                    self.fd = open(self.path,'r')
            except Exception,e:
                raise LogError('Error opening log file %s: %s' % (self.path,e))
        try:
            while True:
                line = self.fd.readline()
                if line == '': 
                    self.fd.close()
                    self.fd = None
                    raise StopIteration
                try:
                    entry = self.logclass(line=line.rstrip(),path=self.path)
                except LogLineTypeError:
                    continue
                except LogError,emsg:
                    if not self.ignore_errors:
                        raise LogError(emsg)
                    self.log.debug(emsg)
                    continue
                if filter_function is None:
                    break
                if filter_function(entry):
                    break

        except IOError,(ecode,emsg):
            raise LogError('Error reading %s: %s' % self.path,emsg)
        except OSError,(ecode,emsg):
            raise LogError('Error reading %s: %s' % self.path,emsg)
        return entry

    def filter(self,function):
        """
        Filter lines from logs with given function.
        """
        entries = []
        while True:
            try:
                entries.append(self.next(function))
            except StopIteration:
                break
        return entries

    def tail(self):
        """
        Keep the log file open, returning new lines when they appear.
        Reopens truncated and replaced files automatically.
        """
        if self.fd is None:
            self.open()
            self.fd.seek(self.stat.st_size)
        while True:
            try:
                stat = os.stat(self.path)
            except OSError,(ecode,emsg):
                if ecode == 2:
                    raise LogError('File was removed: %s' % self.path)
                raise LogError(emsg)

            if stat.st_ino != self.stat.st_ino:
                self.open()
                continue

            if stat.st_size < self.stat.st_size:
                self.open()
                continue

            self.stat = stat
            line = self.fd.readline()
            if line != '': 
                return self.logclass(line=line.rstrip(),path=self.path)

            line = self.fd.readline()
            if line != '': 
                return self.logclass(line=line.rstrip(),path=self.path) 
            time.sleep(1)

class LogEntry(dict):
    """
    Base class for all more specific log entry types
    """
    def __init__(self,line,path=None):
        dict.__init__(self)
        self.path = path
        self.line = line

    def __str__(self):
        return self.line

    def __getattr__(self,item):
        """
        Dynamic attributes:
        date        returns log timestamp formatted as '%Y-%m-%d %H:%M:%S'
        """
        if item == 'date':
            if not self.has_key('timestamp'):
                raise AttributeError('No timestamp defined for log entry')
            return time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(self.timestamp))
        try:
            return self[item]
        except KeyError:
            pass
        raise AttributeError('No such LogEntry attribute: %s' % item)


