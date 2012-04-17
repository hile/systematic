#!/usr/bin/env python
"""
Utility functions for python in unix shell.
"""

import sys,os,time,signal,logging
import logging.handlers
import threading,unicodedata
from optparse import OptionParser
#noinspection PyPackageRequirements
from setproctitle import setproctitle

# Default logging configuration for ScriptLogger
DEFAULT_STREAM_HANDLERS = ['console','modules']
DEFAULT_LOGFORMAT = '%(levelname)s %(message)s'
DEFAULT_LOGFILEFORMAT = \
    '%(asctime)s %(funcName)s[%(process)d] %(levelname)s: %(message)s'
DEFAULT_LOGSIZE_LIMIT = 2**20
DEFAULT_LOG_BACKUPS = 10

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
    __instance = None
    def __init__(self,logformat=DEFAULT_LOGFORMAT,program='python'):
        if ScriptLogger.__instance is None:
            ScriptLogger.__instance = ScriptLogger.__impl(logformat,program)
        self.__dict__['_ScriptLogger__instance'] = ScriptLogger.__instance

    def __getattr__(self,attr):
        if attr == 'level':
            return self.__instance.loglevel
        raise AttributeError('No such ScriptLogger attribute: %s' % attr)

    def __setattr__(self,attr,value):
        if attr in ['level','loglevel']:
            for logger in self.__instance.values():
                logger.setLevel(value)
            self.__instance.__dict__['loglevel'] = value
        else:
            object.__setattr__(self.__instance,attr,value)

    def __getitem__(self,item):
        return self.__instance[item]

    class __impl(dict):
        """
        Singleton implementation of logging configuration for scripts.
        """
        def __init__(self,logformat=DEFAULT_LOGFORMAT,program='python'):
            dict.__init__(self)
            self.program = program
            self.loglevel = logging.Logger.root.level
            self.default_logformat = logformat

            for name in DEFAULT_STREAM_HANDLERS:
                self.stream_handler(name)

        def stream_handler(self,name,logformat=None):
            """
            Register a common log stream handler
            """
            logformat = logformat is not None and logformat or self.default_logformat
            loggers = [l.name for l in logging.Logger.manager.loggerDict.values()]
            if name in loggers:
                return
            logger = logging.getLogger(name)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(logformat))
            logger.addHandler(handler)
            self[name] = logger

        def file_handler(self,name,directory,logformat=None,
                         maxBytes=DEFAULT_LOGSIZE_LIMIT,
                         backupCount=DEFAULT_LOG_BACKUPS):
            """
            Register a common log file handler for rotating file based logs
            """

            logformat = logformat is not None and logformat or self.default_logformat
            loggers = [l.name for l in logging.Logger.manager.loggerDict.values()]
            if name in loggers:
                return
            if not os.path.isdir(directory):
                raise ScriptError('No such directory: %s' % directory)

            logger = logging.getLogger(name)
            logfile = os.path.join(directory,'%s.log' % name)
            handler = logging.handlers.RotatingFileHandler(
                filename=logfile,
                mode='a+',
                maxBytes=maxBytes,
                backupCount=backupCount
            )
            handler.setFormatter(logging.Formatter(logformat))
            logger.addHandler(handler)
            logger.setLevel(self.loglevel)
            self[name] = logger

class ScriptThread(threading.Thread):
    """
    Common script thread base class
    """
    #noinspection PyPropertyAccess
    def __init__(self,name):
        threading.Thread.__init__(self)
        self.daemon = True
        self.name = name
        self.status = 'not running'
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

