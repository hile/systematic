"""
Logging from scripts and parser for syslog files
"""

import os
import re
import bz2
import gzip
import logging
import logging.handlers

from datetime import datetime, timedelta

from systematic.tail import TailReader, TailReaderError

DEFAULT_LOGFORMAT = '%(module)s %(levelname)s %(message)s'
DEFAULT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOGFILEFORMAT = '%(asctime)s %(module)s.%(funcName)s %(message)s'
DEFAULT_LOGSIZE_LIMIT = 2**20
DEFAULT_LOG_BACKUPS = 10

# Default matchers for syslog entry 'host, program, pid' parts
SOURCE_FORMATS = [
    re.compile('^<(?P<version>[^>]+)>\s+(?P<host>[^\s]+)\s+(?P<program>[^\[]+)\[(?P<pid>\d+)\]$'),
    re.compile('^<(?P<version>[^>]+)>\s+(?P<host>[^\s]+)\s+(?P<program>[^\[]+)$'),
    re.compile('^<(?P<facility>\d+)\.(?P<level>\d+)>\s+(?P<host>[^\s]+)\s+(?P<program>[^\[]+)\[(?P<pid>\d+)\]$'),
    re.compile('^<(?P<facility>\d+)\.(?P<level>\d+)>\s+(?P<host>[^\s]+)\s+(?P<program>[^\[]+)$'),
    re.compile('^(?P<host>[^\s]+)\s+(?P<program>[^\[]+)\[(?P<pid>\d+)\]$'),
    re.compile('^(?P<host>[^\s]+)\s+(?P<program>[^\[]+)$'),
]

class LoggerError(Exception):
    """
    Exceptions raised by logging configuration
    """
    def __str__(self):
        return self.args[0]

class Logger(object):
    """
    Singleton class for common logging tasks.
    """
    __instances = {}
    def __init__(self, name=None):
        name = name is not None and name or self.__class__.__name__
        if not Logger.__instances.has_key(name):
            Logger.__instances[name] = Logger.LoggerInstance(name)
        self.__dict__['_Logger__instances'] = Logger.__instances
        self.__dict__['name'] = name

    class LoggerInstance(dict):
        """
        Singleton implementation of logging configuration for one program
        """
        def __init__(self, name):
            self.name = name
            self.loglevel = logging.Logger.root.level
            self.register_stream_handler('default_stream')

        def __getattr__(self, attr):
            if attr in self.keys():
                return self[attr]
            raise AttributeError('No such LoggerInstance attribute: %s' % attr)

        def __setattr__(self, attr, value):
            if attr in ['level', 'loglevel']:
                for logger in self.values():
                    logger.setLevel(value)
                self.__dict__['loglevel'] = value
            else:
                object.__setattr__(self, attr, value)

        def register_stream_handler(self, name, logformat=None, timeformat=None):
            """
            Register a common log stream handler
            """

            if name in self.keys():
                raise LoggerError('Handler name already registered to %s: %s' % (self.name, name))

            if logformat is None:
                logformat = DEFAULT_LOGFORMAT
            if timeformat is None:
                timeformat = DEFAULT_TIME_FORMAT

            for logging_manager in logging.Logger.manager.loggerDict.values():
                if hasattr(logging_manager, 'name') and logging_manager.name==name:
                    self[name] = logging.getLogger(name)
                    return

            logger = logging.getLogger(name)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(logformat, timeformat))
            logger.addHandler(handler)
            self[name] = logger

        def register_file_handler(self, name, directory,
                         logformat=None,
                         maxBytes=DEFAULT_LOGSIZE_LIMIT,
                         backupCount=DEFAULT_LOG_BACKUPS):
            """
            Register a common log file handler for rotating file based logs
            """
            if name in self.keys():
                raise LoggerError('Handler name already registered to %s: %s' % (self.name, name))

            if logformat is None:
                logformat = DEFAULT_LOGFILEFORMAT

            if name in [l.name for l in logging.Logger.manager.loggerDict.values()]:
                return
            if not os.path.isdir(directory):
                try:
                    os.makedirs(directory)
                except OSError:
                    raise LoggerError('Error creating directory: %s' % directory)

            logger = logging.getLogger(name)
            logfile = os.path.join(directory, '%s.log' % name)
            handler = logging.handlers.RotatingFileHandler(
                filename=logfile,
                mode='a+',
                maxBytes=maxBytes,
                backupCount=backupCount
            )
            handler.setFormatter(logging.Formatter(logformat, self.timeformat))
            logger.addHandler(handler)
            logger.setLevel(self.loglevel)
            self[name] = logger

        @property
        def level(self):
            return self.loglevel

        def set_level(self, value):
            if not hasattr(logging, value):
                raise LoggerError('Invalid logging level: %s' % value)
            level = getattr(logging, value)
            if not isinstance(level, int):
                raise LoggerError('Not integer value: %s (%s)' % (value, type(level)))
            self.loglevel = level

    def __getattr__(self, attr):
        return getattr(self.__instances[self.name], attr)

    def __setattr__(self, attr, value):
        setattr(self.__instances[self.name], attr, value)

    def __getitem__(self, item):
        return self.__instances[self.name][item]

    def __setitem__(self, item, value):
        self.__instances[self.name][item] = value


class LogFileError(Exception):
    """
    Exceptions from logfile parsers
    """
    pass


class LogEntry(object):
    """
    Generic syslog logfile entry
    """
    def __init__(self, line, year, source_formats):
        line = line.rstrip()
        self.line = line

        self.version = None
        self.host = None
        self.program = None
        self.pid = None

        try:
            mon, day, time, line = line.split(None, 3)
        except ValueError:
            raise LogFileError('Error splitting log line: %s' % self.line)

        try:
            self.time = datetime.strptime('%s %s %s %s' % (year, mon, day, time), '%Y %b %d %H:%M:%S')
        except ValueError:
            raise LogFileError('Error parsing entry time from line: %s' % self.line)

        try:
            self.source, self.message = [x.strip() for x in line.split(':', 1)]
            for fmt in source_formats:
                m = fmt.match(self.source)
                if m:
                    for k, v in m.groupdict().items():
                        setattr(self, k, v)
                    break

        except ValueError:
            # Lines like '--- last message repeated 2 times ---'
            self.source = None
            self.message = line

    def __repr__(self):
        return '%s %s%s%s' % (
            self.time.strftime('%Y-%m-%d %H:%M:%S'),
            self.program is not None and '%s ' % self.program or '',
            self.pid is not None and '(%s) ' % self.pid or '',
            self.message
        )

    def append(self, message):
        self.message = '%s\n%s' % (self.message, message.rstrip())


class LogFile(list):
    """
    Generic syslog file parser
    """
    def __init__(self, path, source_formats=SOURCE_FORMATS):
        if isinstance(path, basestring):
            self.path = os.path.expanduser(os.path.expandvars(path))
        else:
            self.path = path

        self.source_formats = source_formats
        self.lineloader = LogEntry
        self.mtime = None

        self.__iter_index = None
        self.__loaded = False
        self.fd = None

    def __repr__(self):
        return '%s %s entries' % (self.path, len(self))

    def __iter__(self):
        return self

    def __open_logfile__(self, path):
        """Try opening log file

        Try opening logfile in gz, bz2 and raw text formats

        """
        try:
            fd = gzip.GzipFile(path)
            fd.readline()
            fd.seek(0)
            return fd
        except IOError:
            pass

        try:
            fd = bz2.BZ2File(path)
            fd.readline()
            fd.seek(0)
            return fd
        except IOError:
            pass

        try:
            fd = open(path, 'r')
            fd.readline()
            fd.seek(0)
            return fd
        except IOError:
            pass

        raise LogFileError('Error opening logfile %s' % self.path)

    def next(self):
        if not self.__loaded:
            # Load file on the fly and cache entries
            if self.fd == None:
                if isinstance(self.path, file):
                    self.fd = self.path
                    self.mtime = datetime.now()
                else:
                    try:
                        self.fd = self.__open_logfile__(self.path)
                        self.mtime = datetime.fromtimestamp(os.stat(self.path).st_mtime)
                    except OSError, (ecode, emsg):
                        raise LogFileError('Error opening %s: %s' % (self.path, emsg))
            entry = self.readline()

            if entry is None:
                raise StopIteration
            return entry

        else:
            # Iterate cached entries
            if self.__iter_index is None:
                self.__iter_index = 0

            try:
                entry = self[self.__iter_index]
                self.__iter_index += 1
                return entry
            except IndexError:
                self.__iter_index = None
                raise StopIteration

    def readline(self):
        """
        Load whole log file
        """
        if self.fd is None:
            raise LogFileError('File was not loaded')
        try:
            l = self.fd.readline()
            if l == '':
                self.__loaded = True
                return None

            # Multiline log entry
            if l[:1] in [' ', '\t'] and entry:
                entry.append(l)
                return self.readline()

            else:
                entry = self.lineloader(l, year=self.mtime.year, source_formats=self.source_formats)
                self.append(entry)
                return entry

        except OSError, (ecode, emsg):
            raise LogFileError('Error reading file %s: %s' % (self.path, emsg))

    def reload(self):
        list.__delslice__(self, 0, len(self))
        self.__loaded = False
        while True:
            try:
                entry = self.next()
            except StopIteration:
                break

    def filter_host(self, host):
        """Filter by host name

        Return log entries matching given host name

        """
        if len(self) == 0:
            self.reload()
        return [x for x in self if x.host == host]

    def filter_program(self, program):
        """Filter by program name

        Return log entries matching given program name

        """
        if len(self) == 0:
            self.reload()
        return [x for x in self if x.program == program]

    def filter_message(self, message_regexp):
        """Filter by message regexp

        Filter log entries matching given regexp in message field

        """
        if len(self) == 0:
            self.reload()

        if isinstance(message_regexp, basestring):
            message_regexp = re.compile(message_regexp)

        return [x for x in self if message_regexp.match(x.message)]

    def match_message(self, message_regexp):
        """

        Return dictionary of matching regexp keys for lines matching given regexp
         in message field

        """
        if len(self) == 0:
            self.reload()

        if isinstance(message_regexp, basestring):
            message_regexp = re.compile(message_regexp)

        matches = []
        for x in self:
            m = message_regexp.match(x.message)
            if not m:
                continue
            matches.append(m.groupdict())
        return matches


class LogFileCollection(object):
    """Process multiple logfiles

    Load, iterate and process multiple log files. Typical usage would be like:

        lc = LogFileCollection(glob.glob('/var/log/auth.log*'))

    Files are sorted by modification timestamp and name.

    """
    def __init__(self, logfiles, source_formats=SOURCE_FORMATS):
        self.source_formats = source_formats
        self.logfiles = []
        self.__iter_index = None
        self.__iter_entry = None

        stats = {}
        for path in logfiles:
            try:
                st = os.stat(path)
                ts = long(st.st_mtime)
                if ts not in stats.keys():
                    stats[ts] = []
                stats[ts].append(path)

            except OSError, (ecode, emsg):
                raise LogFileError('Error running stat on %s: %s' % (path, emsg))
            except IOError, (ecode, emsg):
                raise LogFileError('Error running stat on %s: %s' % (path, emsg))

        for ts in stats.keys():
            stats[ts].sort()

        for ts in sorted(stats.keys()):
            self.logfiles.extend(LogFile(path, source_formats=self.source_formats) for path in stats[ts])

    def __repr__(self):
        return 'collection of %d logfiles' % len(self.logfiles)

    def __iter__(self):
        return self

    def next(self):
        if not self.logfiles:
            raise StopIteration

        if self.__iter_index is None:
            self.__iter_index = 0
            self.__iter_entry = self.logfiles[0]

        try:
            logentry = self.__iter_entry.next()

        except StopIteration, emsg:
            if self.__iter_index < len(self.logfiles) - 1:
                self.__iter_index += 1
                self.__iter_entry = self.logfiles[self.__iter_index]

                try:
                    logentry = self.__iter_entry.next()
                except StopIteration:
                    self.__iter_index = None
                    self.__iter_entry = None
                    raise StopIteration

            else:
                self.__iter_index = None
                self.__iter_entry = None
                raise StopIteration

        return logentry

    def filter_host(self, host):
        """Filter by host

        Filter all loaded logfiles by matching host with LogFile.filter_host

        """
        matches = []
        for parser in self.logfiles:
            matches.extend(parser.filter_host(host))
        return matches

    def filter_program(self, program):
        """Filter by program

        Filter all loaded logfiles by matching program with LogFile.filter_program

        """
        matches = []
        for parser in self.logfiles:
            matches.extend(parser.filter_program(program))
        return matches

    def filter_message(self, message_regexp):
        """Filter messages by regexp

        Match all loaded logfiles by matching program with LogFile.filter_message

        """
        if isinstance(message_regexp, basestring):
            message_regexp = re.compile(message_regexp)

        matches = []
        for parser in self.logfiles:
            matches.extend(parser.filter_message(message_regexp))
        return matches

    def match_message(self, message_regexp):
        """Match messages by regexp

        Match all loaded logfiles by matching program with LogFile.match_message

        """
        if isinstance(message_regexp, basestring):
            message_regexp = re.compile(message_regexp)

        matches = []
        for parser in self.logfiles:
            matches.extend(parser.match_message(message_regexp))
        return matches


class LogfileTailReader(TailReader):
    """Logfile tail reader

    Tail reader returning LogFile entries

    """
    def __init__(self, path=None, fd=None, source_formats=SOURCE_FORMATS):
        TailReader.__init__(self, path, fd)
        self.source_formats = source_formats

    def __format_line__(self, line):
         return LogEntry(line[:-1], self.year, source_formats=self.source_formats)
