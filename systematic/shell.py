"""
Utility functions for python in unix shell.
"""

import sys
import os
import time
import signal
import socket
import argparse
import threading
import unicodedata

from Queue import Queue, Empty

from systematic.classes import check_output, CalledProcessError
from subprocess import Popen, PIPE
from setproctitle import setproctitle

from systematic.log import Logger

if sys.platform=='darwin':
    CONFIG_PATH = os.path.expanduser('~/Library/Application Support/Systematic')
else:
    CONFIG_PATH = os.path.expanduser('~/.config/systematic')

# Values for TERM environment variable which support setting title
TERM_TITLE_SUPPORTED = ( 'xterm', 'xterm-debian' )


def xterm_title(value, max_length=74, bypass_term_check=False):
    """
    Set title in xterm titlebar to given value, clip the title text to
    max_length characters.
    """
    #if not os.isatty(1): return

    TERM=os.getenv('TERM')
    if not bypass_term_check and TERM not in TERM_TITLE_SUPPORTED:
        return
    sys.stderr.write('\033]2;'+value[:max_length]+'', )
    sys.stderr.flush()


def normalized(path, normalization='NFC'):
    """
    Return given path value as normalized unicode string on OS/X,
    on other platform return the original string as unicode
    """
    if sys.platform != 'darwin':
        return type(path)==unicode and path or unicode(path, 'utf-8')
    if not isinstance(path, unicode):
        path = unicode(path, 'utf-8')
    return unicodedata.normalize(normalization, path)


class ScriptError(Exception):
    pass


class CommandPathCache(list):
    """
    Class to represent commands on user's search path.
    """
    def __init__(self):
        self.update()

    def update(self):
        """
        Updates the commands available on user's PATH
        """
        paths = []
        self.__delslice__(0, len(self))

        for path in os.getenv('PATH').split(os.pathsep):
            if not paths.count(path):
                paths.append(path)

        for path in paths:
            if not os.path.isdir(path):
                continue
            for cmd in [os.path.join(path, f) for f in os.listdir(path)]:
                if os.path.isdir(cmd) or not os.access(cmd, os.X_OK):
                    continue
                self.append(cmd)

    def versions(self, name):
        """
        Returns all commands with given name on path, ordered by PATH search
        order.
        """
        if not len(self):
            self.update()
        return filter(lambda x: os.path.basename(x) == name, self)

    def which(self, name):
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


class ScriptThread(threading.Thread):
    """
    Common script thread base class
    """
    def __init__(self, name):
        super(threading.Thread, self).__init__()
        self.log = Logger(name).default_stream
        self.status = 'not running'
        self.setDaemon(True)
        self.setName(name)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    @property
    def stopped(self):
        return self._stop_event.isSet()

    def execute(self, command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
        p = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr)
        p.wait()
        return p.returncode


class ScriptThreadManager(list):
    """Script Thread Manager

    Run script threads with maximum concurrency of

    """
    def __init__(self, threads=1):
        self.threads = threads
        self.messages = Queue()

    def process_messages(self):
        while True:
            try:
                line = self.messages.get(timeout=1)
            except Empty:
                return
            else:
                sys.stdout.write('{0}\n'.format(line))

    def run(self):
        total = len(self)

        while len(self) > 0:
            self.process_messages()

            active = threading.active_count()
            if active > self.threads:
                time.sleep(0.1)

            else:
                t = self.pop(0)
                t.start()

        while threading.active_count() > 1:
            self.process_messages()
            time.sleep(0.1)

        self.process_messages()


class Script(object):
    """
    Class for common CLI tool script
    """
    def __init__(self, name=None, description=None, epilog=None, debug_flag=True):
        self.name = os.path.basename(sys.argv[0])
        setproctitle('{0} {1}'.format(self.name, ' '.join(sys.argv[1:])))
        signal.signal(signal.SIGINT, self.SIGINT)

        reload(sys)
        sys.setdefaultencoding('utf-8')

        if name is None:
            name = self.name

        # Set to True to avoid any messages from self.message to be output
        self.silent = False

        self.logger = Logger(self.name)
        self.log = self.logger.default_stream

        self.parser = argparse.ArgumentParser(
            prog=name,
            description=description,
            formatter_class=argparse.RawTextHelpFormatter,
            epilog=epilog,
            add_help=True,
            conflict_handler='resolve',
        )

        if debug_flag:
            self.parser.add_argument('--debug', action='store_true', help='Show debug messages')

        self.subcommand_parser = None

    def SIGINT(self, signum, frame):
        """
        Parse SIGINT signal by quitting the program cleanly with exit code 1
        """
        for t in filter(lambda t: t.name!='MainThread', threading.enumerate()):
            if hasattr(t, 'stop') and callable(t.stop):
                t.stop()

        for t in filter(lambda t: t.name!='MainThread', threading.enumerate()):
            t.join()

        self.exit(1)

    def wait(self, poll_interval=1):
        """
        Wait for running threads to finish.
        Poll interval is time to wait between checks for threads
        """
        while True:
            active = filter(lambda t: t.name!='MainThread', threading.enumerate())
            if not len(active):
                break
            self.log.debug('Waiting for {0:d} threads'.format(len(active)))
            time.sleep(poll_interval)

    def exit(self, value=0, message=None):
        """
        Exit the script with given exit value.
        If message is not None, it is output to stdout
        """
        if isinstance(value, bool):
            if value:
                value = 0
            else:
                value = 1
        else:
            try:
                value = int(value)
                if value < 0 or value > 255:
                    raise ValueError
            except ValueError:
                value = 1

        if message is not None:
            self.message(message)

        for t in filter(lambda t: t.name!='MainThread', threading.enumerate()):
            if hasattr(t, 'stop') and callable(t.stop):
                t.stop()

        while True:
            active = filter(lambda t: t.name!='MainThread', threading.enumerate())
            if not len(active):
                break
            time.sleep(0.1)

        sys.exit(value)

    def message(self, message):
        if self.silent:
            return
        sys.stdout.write('{0}\n'.format(message))

    def error(self, message):
        sys.stderr.write('{0}\n'.format(message))

    def add_subcommand(self, command):
        """Add a subcommand parser instance

        Register named subcommand parser to argument parser

        Subcommand parser must be an instance of ScriptCommand class.

        Example usage:

        class ListCommand(ScriptCommand):
            def run(self, args):
                self.message('Listing stuff')

        parser.add_subcommand(ListCommand('list', 'List stuff from script'))

        """

        if self.subcommand_parser is None:
            self.subcommand_parser = self.parser.add_subparsers(
                dest='command', help='Please select one command mode below',
                title='Command modes'
            )
            self.subcommands = {}

        if not isinstance(command, ScriptCommand):
            raise ScriptError('Subcommand must be a ScriptCommand instance')

        parser = self.subcommand_parser.add_parser(
            command.name,
            help=command.short_description,
            description=command.description,
            epilog=command.epilog,
            formatter_class=argparse.RawTextHelpFormatter,
        )
        self.subcommands[command.name] = command
        command.script = self

        return parser

    def usage_error(self, *args, **kwargs):
        return self.parser.error(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        """
        Shortcut to add argument to main argumentparser instance
        """
        self.parser.add_argument(*args, **kwargs)

    def __process_args__(self, args):
        """Process args
        Process args from parse_*args CalledProcessError
        """
        if hasattr(args, 'debug') and getattr(args, 'debug'):
            self.logger.set_level('DEBUG')

        elif hasattr(args, 'quiet') and getattr(args, 'quiet'):
            self.silent = True

        elif hasattr(args, 'verbose') and getattr(args, 'verbose'):
            self.logger.set_level('INFO')

        if self.subcommand_parser is not None:
            self.subcommands[args.command].run(args)

        return args

    def parse_args(self):
        """
        Call parse_args for parser and check for default logging flags
        """
        return self.__process_args__(self.parser.parse_args())

    def parse_known_args(self):
        """
        Call parse_args for parser and check for default logging flags
        """
        args, other_args = self.parser.parse_known_args()
        args = self.__process_args__(args)
        return args, other_args

    def execute(self, args, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, dryrun=False):
        """
        Default wrapper to execute given interactive shell command
        with standard stdin, stdout and stderr
        """
        if isinstance(args, basestring):
            args = args.split()

        if not isinstance(args, list):
            raise ValueError('Execute arguments must be a list')

        if dryrun:
            self.log.debug('would execute: {0}'.format(' '.join(args)))
            return 0

        p = Popen(args, stdin=stdin, stdout=stdout, stderr=stderr)
        p.wait()
        return p.returncode

    def check_output(self, args):
        """
        Wrapper for subprocess.check_output to be executed in script context
        """
        if isinstance(args, basestring):
            args = [args]
        try:
            return check_output(args)

        except IOError, (ecode, emsg):
            raise ScriptError(emsg)

        except OSError, (ecode, emsg):
            raise ScriptError(emsg)

        except CalledProcessError, emsg:
            raise ScriptError(emsg)


class ScriptCommand(argparse.ArgumentParser):
    """Script subcommand parser class

    Parser for Script subcommands.

    Implement custom logic to this class and provide a custom
    parse_args to call these methods as required

    """
    def __init__(self, name, short_description='', description='', epilog=''):
        self.script = None
        self.name = name
        self.short_description = short_description
        self.description = description
        self.epilog = epilog

    @property
    def log(self):
        return self.script.log

    def exit(self, value=0, message=None):
        self.script.exit(value, message)

    def wait(self, poll_interval=1):
        self.script.wait(poll_interval=1)

    def execute(self, *args, **kwargs):
        return self.script.execute(*args, **kwargs)

    def check_output(self, *args, **kwargs):
        return self.script.check_output(*args, **kwargs)

    def message(self, message):
        return self.script.message(message)

    def run(self, args):
        """Run subcommands

        This method is called from parent script parse_args with
        processed arguments, when a subcommand has been registered

        Implement your subcommand logic here.

        """
        sys.stderr.write('Subcommand {0} has no run method implemented\n'.format(self.name))
