#!/usr/bin/env python
"""
Utility functions for python in unix shell.
"""

import sys,os,time,signal,logging
import threading,inspect,ctypes,unicodedata
from optparse import OptionParser
from setproctitle import setproctitle

# Values for TERM environment variable which support setting title
TERM_TITLE_SUPPORTED = [ 'xterm','xterm-debian']

def normalized(path):
    """
    Return given path value as normalized unicode string on OS/X, on other
    platform return the original string as unicode
    """
    if sys.platform != 'darwin':
        return type(path)==unicode and path or unicode(path,'utf-8')
    return unicodedata.normalize( 
        'NFC', type(path)==unicode and path or unicode(path,'utf-8')
    )

class CommandPathCache(list):
    """
    Class to represent commands on user's search path.
    """
    def __init__(self):
        self.paths = None
        self.update()

    def update(self):
        """
        Updates the commands available on user's PATH
        """
        self.paths = []
        self.__delslice__(0,len(self))
        for path in os.getenv('PATH').split(os.pathsep):
            if self.paths.count(path) == 0:
                self.paths.append(path)
        for path in self.paths:
            for cmd in [os.path.join(path,f) for f in os.listdir(path)]:
                if os.path.isdir(cmd) or not os.access(cmd,os.X_OK):
                    continue
                self.append(cmd)

    def versions(self,name):
        """
        Returns all commands with given name on path, ordered by PATH search
        order.
        """ 
        if len(self) == 0:
            self.update()
        return filter(lambda x: os.path.basename(x) == name, self)

    def which(self,name):
        """
        Return first matching path to command given with name, or None if 
        command is not on path
        """
        if len(self) == 0:
            self.update()
        try:
            return filter(lambda x: os.path.basename(x) == name, self)[0]
        except IndexError:
            return None

def xterm_title(value,max_lenght=74,bypass_term_check=False):
    """
    Set title in xterm titlebar to given value, clip the title text to 
    max_length characters.
    """ 
    TERM=os.getenv('TERM')
    if not bypass_term_check and TERM not in TERM_TITLE_SUPPORTED:
        return
    sys.stdout.write('\033]2;'+value[:max_length]+'',)
    sys.stdout.flush()

def Interrupted(signum,frame):
    for t in filter(lambda t: t.name!='MainThread', threading.enumerate()):
        t.join()
    sys.exit(1)

class ScriptThread(threading.Thread):
    """
    Common execution thread base class
    """
    def __init__(self,name):
        threading.Thread.__init__(self)
        self.daemon = True
        self.name = name
        self.status = 'not running'
        self.log = logging.getLogger('modules')

class PythonScript(object):
    """
    Wrapper class for common python shell script
    """
    def __init__(self):
        self.name = os.path.basename(sys.argv[0])
        setproctitle('%s %s' % (self.name,' '.join(sys.argv[1:])))
        signal.signal(signal.SIGINT, Interrupted)

        reload(sys)
        sys.setdefaultencoding('utf-8')

        self.parser = OptionParser()
        self.log = logging.getLogger('console')
        self.parser.add_option('-v','--verbose',dest='verbose',
            action='store_true',help='Show verbose messages'
        )

    def set_usage(self,*args,**kwargs):
        return self.parser.set_usage(*args,**kwargs)

    def set_defaults(self,*args,**kwargs):
        return self.parser.set_defaults(*args,**kwargs)

    def get_usage(self):
        return self.parser.get_usage()

    def add_option(self,*args,**kwargs):
        return self.parser.add_option(*args,**kwargs)

    def parse_args(self):
        (opts,args) = self.parser.parse_args()
        if opts.verbose:
            logging.basicConfig(level=logging.INFO)
        return (opts,args)

    def exit(self,value,message=None):
        if message is not None:
            print message
        while True:
            active = filter(lambda t: t.name!='MainThread', threading.enumerate())
            if len(active) == 0:
                break
            time.sleep(1)
        sys.exit(value)

def uniq(lines,count=False,duplicates=False,unique=False,ignore_case=False,
    field=0,char_offset=0):
    """
    Function similar to unix uniq against given input lines.

    Options:
    lines:  iterable strings to process
    count:  print number of occurrances for each line (-c)
    duplicates: print only lines where there are more than one match (-d)
    unique: print only unique lines (-u)
    ignore_case: match lines case insensitively (-i)
    field: start matching from given space separated field (-f num)
    char_offset: start from char count offset from beginning of match (-s num)
    """

    return []

