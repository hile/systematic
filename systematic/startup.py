"""Init scripts

Wrapper to implement init scripts for python programs

"""

import sys
import os
import logging
import argparse
from subprocess import check_output, Popen, PIPE

LOGGING_FORMAT = '%(asctime)s %(name)s %(message)s'
LOGGING_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger(__file__)

class InitScriptError(Exception):
    pass

class InitScript(object):
    """Init script

    Implement common init scripts in python.

    Example init script to start supervisord from virtualenv:

    #!/usr/bin/env python
    #
    # Start supervisord from virtualenv
    #

    from systematic.startup import InitScript

    ROOT = os.sep.join(os.path.realpath(__file__).split(os.sep)[:-2])
    daemon = os.path.join(ROOT, 'virtualenv', 'bin', 'supervisord')
    pidfile = os.path.join(ROOT, 'var', 'run', 'supervisord.pid')

    InitScript(__file__, daemon, pidfile).run()

    """
    def __init__(self, script, daemon, pidfile, daemon_args=[], valid_commands=('start', 'stop', 'restart', 'status')):
        self.name = os.path.basename(os.path.realpath(script))
        self.daemon = daemon
        self.daemon_args = daemon_args
        self.pidfile = pidfile

        self.parser = argparse.ArgumentParser(self.name)
        self.parser.add_argument('--debug', action='store_true', help='Show debug messages')
        self.parser.add_argument('command', choices=valid_commands, help='Control option')

    @property
    def pid(self):
        """Return PID from pidfile

        Read the PID file and return PID found in the file

        """
        if not os.path.isfile(self.pidfile):
            logger.debug('No such file: %s' % self.pidfile)
            return False

        if not os.access(self.pidfile, os.R_OK):
            logger.debug('Not readable: %s' % self.pidfile)
            return False

        p = Popen(['pgrep', '-F', self.pidfile], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout,sterr) = p.communicate()
        if p.returncode != 0:
            return None

        try:
            return int(stdout.strip())
        except ValueError:
            raise InitScriptError('invalid pidfile contents: %s' % pidfile)

    @property
    def is_running(self):
        """Check if service is running

        Returns True, if pidfile is specified and pgreg -F finds the process

        """
        if not os.path.isfile(self.pidfile):
            logger.debug('No such file: %s' % self.pidfile)
            return False

        if not os.access(self.pidfile, os.R_OK):
            logger.debug('Not readable: %s' % self.pidfile)
            return False

        p = Popen(['pgrep', '-F', self.pidfile], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()
        return p.returncode == 0

    def error(self, message, code=1):
        """Print error and exit

        Print specified error message to stderr and exit with error code

        """
        try:
            code = int(code)
        except ValueError:
            code = 1

        sys.stderr.write('%s\n' % message)
        sys.exit(code)

    def fail(self, code):
        self.message('ERROR\n')
        sys.exit(code)

    def ok(self, code):
        self.message('OK\n')
        sys.exit(0)

    def message(self, message):
        sys.stdout.write('%s' % message)

    def parse_args(self):
        """Parse arguments
        """
        args = self.parser.parse_args()
        if args.debug:
            logging.basicConfig(level=logging.DEBUG, format=LOGGING_FORMAT, datefmt=LOGGING_TIME_FORMAT)

        return args

    @property
    def status(self):
        """
        """
        if self.is_running:
            self.message('Running: %s (pid %s)\n' % (self.name, self.pid))
        else:
            self.message('Not running: %s\n' % (self.name))

    @property
    def stop(self):
        """Stop service

        Stop the service if PID file was not found

        """
        if not self.is_running:
            raise InitScriptError('%s: not running' % (self.name))

        self.message('Stopping: %s (pid %s)' % (self.name, self.pid))
        command = ['pkill', '-F', self.pidfile]
        p = Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()
        if p.returncode != 0:
            self.fail(p.returncode)
        self.ok()

    @property
    def start(self):
        """Start service

        Start the service if PID file was not found

        """
        if self.is_running:
            self.error('%s: already running (pid %s)' % (self.name, self.pid))

        self.message('Starting: %s' % (self.name))
        command = [self.daemon] + self.daemon_args
        p = Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()
        if p.returncode != 0:
            self.fail(p.returncode)
        self.ok()

    def run(self):
        """Run init script

        Parse command line arguments and execute given command

        """
        args = self.parse_args()
        try:
            callback = getattr(self, args.command)
        except AttributeError:
            self.error(code=1, message='Function not implemented: %s' % args.command)

        try:
            return callback()
        except InitScriptError,emsg:
            self.error(code=1, message=emsg)
