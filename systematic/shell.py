#!/usr/bin/env python
"""
Utility functions for python in unix shell.
"""

import sys,os,time,signal,logging,socket
import logging.handlers
import threading,unicodedata
from subprocess import Popen,PIPE

from optparse import OptionParser

#noinspection PyPackageRequirements
from setproctitle import setproctitle

# Default logging configuration for ScriptLogger
DEFAULT_STREAM_HANDLERS = ['console','modules']
DEFAULT_LOGFORMAT = '%(levelname)s %(message)s'
DEFAULT_LOGFILEFORMAT = \
    '%(asctime)s %(module)s.%(funcName)s %(message)s'
DEFAULT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOGSIZE_LIMIT = 2**20
DEFAULT_LOG_BACKUPS = 10
# Syslog logger parameters
DEFAULT_SYSLOG_LOGFORMAT = '%(name)s %(levelname)s %(message)s'

# Values for TERM environment variable which support setting title
TERM_TITLE_SUPPORTED = [ 'xterm','xterm-debian']

def normalized(path,normalization='NFC'):
    """
    Return given path value as normalized unicode string on OS/X, on other
    platform return the original string as unicode
    """
    if sys.platform != 'darwin':
        return type(path)==unicode and path or unicode(path,'utf-8')
    return unicodedata.normalize( 
        normalization, type(path)==unicode and path or unicode(path,'utf-8')
    )

class CommandPathCache(list):
    """
    Class to represent commands on user's search path.
    """
    def __init__(self):
        list.__init__(self)
        self.paths = None
        self.update()

    def update(self):
        """
        Updates the commands available on user's PATH
        """
        self.paths = []
        self.__delslice__(0,len(self))
        for path in os.getenv('PATH').split(os.pathsep):
            if not self.paths.count(path):
                self.paths.append(path)
        for path in self.paths:
            if not os.path.isdir(path):
                continue
            for cmd in [os.path.join(path,f) for f in os.listdir(path)]:
                if os.path.isdir(cmd) or not os.access(cmd,os.X_OK):
                    continue
                self.append(cmd)

    def versions(self,name):
        """
        Returns all commands with given name on path, ordered by PATH search
        order.
        """ 
        if not len(self):
            self.update()
        return filter(lambda x: os.path.basename(x) == name, self)

    def which(self,name):
        """
        Return first matching path to command given with name, or None if 
        command is not on path
        """
        if not len(self):
            self.update()
        try:
            return filter(lambda x: os.path.basename(x) == name, self)[0]
        except IndexError:
            return None

def xterm_title(value,max_length=74,bypass_term_check=False):
    """
    Set title in xterm titlebar to given value, clip the title text to 
    max_length characters.
    """ 
    TERM=os.getenv('TERM')
    if not bypass_term_check and TERM not in TERM_TITLE_SUPPORTED:
        return
    sys.stdout.write('\033]2;'+value[:max_length]+'',)
    sys.stdout.flush()

class ScriptError(Exception):
    """
    Exceptions raised by running scripts
    """
    def __str__(self):
        return self.args[0]

class ScriptLogger(object):
    """
    Class for common script logging tasks. Implemented as singleton to prevent
    errors in duplicate handler initialization.
    """
    __instances = {}
    def __init__(self,program='python',logformat=DEFAULT_LOGFORMAT):
        if not ScriptLogger.__instances.has_key(program):
            ScriptLogger.__instances[program] = ScriptLogger.ScriptLoggerInstance(    
                program,logformat
            )
        self.__dict__['_ScriptLogger__instances'] = ScriptLogger.__instances
        self.__dict__['program'] = program

        for name in DEFAULT_STREAM_HANDLERS:
            self.stream_handler(name)

    class ScriptLoggerInstance(dict):
        """
        Singleton implementation of logging configuration for one program
        """
        def __init__(self,program,logformat,timeformat=DEFAULT_TIME_FORMAT):
            dict.__init__(self)
            self.program = program
            self.loglevel = logging.Logger.root.level
            self.default_logformat = logformat
            self.timeformat = timeformat

        def __getattr__(self,attr):
            if attr == 'level':
                return self.loglevel
            raise AttributeError('No such ScriptLoggerInstance attribute: %s' % attr)

        def __setattr__(self,attr,value):
            if attr in ['level','loglevel']:
                for logger in self.values():
                    logger.setLevel(value)
                self.__dict__['loglevel'] = value
            else:
                object.__setattr__(self,attr,value)

    def __getattr__(self,attr):
        return getattr(self.__instances[self.program],attr)

    def __setattr__(self,attr,value):
        setattr(self.__instances[self.program],attr,value)

    def __getitem__(self,item):
        return self.__instances[self.program][item]

    def __setitem__(self,item,value):
        self.__instances[self.program][item] = value

    def stream_handler(self,name,logformat=None):
        """
        Register a common log stream handler
        """
        if logformat is None:
            logformat = self.default_logformat 
        if name in [l.name for l in logging.Logger.manager.loggerDict.values()]:
            return

        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(logformat,self.timeformat))
        logger.addHandler(handler)
        self[name] = logger

    def file_handler(self,name,directory,logformat=None,
                     maxBytes=DEFAULT_LOGSIZE_LIMIT,
                     backupCount=DEFAULT_LOG_BACKUPS):
        """
        Register a common log file handler for rotating file based logs
        """
        if logformat is None:
            logformat = DEFAULT_LOGFILEFORMAT
        if name in [l.name for l in logging.Logger.manager.loggerDict.values()]:
            return
        if not os.path.isdir(directory):
            try:
                os.makedirs(directory)
            except OSError:
                raise ScriptError('Error creating directory: %s' % directory)

        logger = logging.getLogger(name)
        logfile = os.path.join(directory,'%s.log' % name)
        handler = logging.handlers.RotatingFileHandler(
            filename=logfile,
            mode='a+',
            maxBytes=maxBytes,
            backupCount=backupCount
        )
        handler.setFormatter(logging.Formatter(logformat,self.timeformat))
        logger.addHandler(handler)
        logger.setLevel(self.loglevel)
        self[name] = logger

    def syslog_handler(self,name,facility=None,address=None,logformat=None):
        """
        Register a handler writing to syslog services.

        The priority is decided by SysLogHandler based on log level and
        can't be altered from here. 
        """
        if logformat is None:   
            logformat = DEFAULT_SYSLOG_LOGFORMAT
        if facility is None:
            facility = 'daemon'
        
        if address is None:
            if os.path.exists('/dev/log'):
                address = '/dev/log'
            else:
                # TODO - check if this actually works, did not see it 
                # while developing this, but might have been syslog config
                # issue!
                address = ('localhost',logging.handlers.SYSLOG_UDP_PORT)
        self.address = address

        try:
            handler = logging.handlers.SysLogHandler(address,facility)
        except socket.error,(ecode,emsg):
            raise ScriptError('Error creating SysLogHandler: %s' % emsg)
        handler.setFormatter(logging.Formatter(logformat,self.timeformat))
        handler.mapPriority(self.level)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)
        self.logger.addHandler(handler)

class ScriptThread(threading.Thread):
    """
    Common script thread base class
    """
    def __init__(self,name):
        threading.Thread.__init__(self)
        self.status = 'not running'
        self.setDaemon(True)
        self.setName(name)
        self.logger = ScriptLogger()
        self.log = logging.getLogger('modules')

class Script(object):
    """
    Class for common CLI tool script
    """
    def __init__(self):
        self.name = os.path.basename(sys.argv[0])
        setproctitle('%s %s' % (self.name,' '.join(sys.argv[1:])))
        signal.signal(signal.SIGINT, self.SIGINT)

        reload(sys)
        sys.setdefaultencoding('utf-8')

        self.logger = ScriptLogger()
        self.log = logging.getLogger('console')

        self.parser = OptionParser()
        self.parser.add_option('-v','--verbose',dest='verbose',
            action='store_true',help='Show verbose messages'
        )
        self.parser.add_option('-d','--debug',dest='debug',
            action='store_true',help='Show debug messages'
        )

    #noinspection PyUnusedLocal,PyUnusedLocal
    def SIGINT(self,signum,frame):
        """
        Parse SIGINT signal by quitting the program cleanly with exit code 1
        """
        for t in filter(lambda t: t.name!='MainThread', threading.enumerate()):
            t.join()
        self.exit(1)

    def set_usage(self,*args,**kwargs):
        """
        Set command usage help text. See optparse.OptionParser for usage
        """
        return self.parser.set_usage(*args,**kwargs)

    def get_usage(self):
        """
        Get command usage help text. See optparse.OptionParser for usage
        """
        return self.parser.get_usage()

    def set_defaults(self,*args,**kwargs):
        """
        Set option defaults. See optparse.OptionParser for usage
        """
        return self.parser.set_defaults(*args,**kwargs)

    def add_option(self,*args,**kwargs):
        """
        Add command line option. See optparse.OptionParser for usage
        """
        return self.parser.add_option(*args,**kwargs)

    def wait(self,poll_interval=1):
        """
        Wait for running threads to finish. 
        Poll interval is time to wait between checks for threads
        """
        while True:
            active = filter(lambda t: t.name!='MainThread', threading.enumerate())
            if not len(active):
                break
            self.log.debug('Waiting for %d threads' % len(active))
            time.sleep(poll_interval)

    def exit(self,value=0,message=None):
        """
        Exit the script with given exit value.
        If message is not None, it is printed on screen.
        """
        if message is not None:
            print message
        while True:
            active = filter(lambda t: t.name!='MainThread', threading.enumerate())
            if not len(active):
                break
            time.sleep(1)
        sys.exit(value)

    def parse_args(self):
        """
        Call parse_args for parser and check for default logging flags
        """
        (opts,args) = self.parser.parse_args()
        if opts.verbose:
            self.logger.level = logging.INFO
        if opts.debug:
            self.logger.level = logging.DEBUG

        return opts,args

    def execute(self,args,dryrun=False):
        """
        Default wrapper to execute given interactive shell command 
        """
        if not isinstance(args,list):
            raise ValueErro('Execute arguments must be a list')
        if not dryrun:
            self.log.debug('EXECUTE: %s' % ' '.join(args))
            p = Popen(args, 
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            p.wait()
            return p.returncode


