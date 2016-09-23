"""
Init scripts

Wrapper to implement init scripts for python programs

"""

import sys
import os
import logging
import argparse
from subprocess import Popen, PIPE

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

    def error(self, message, code=1):
        """Print error and exit

        Print specified error message to stderr and exit with error code

        """
        try:
            code = int(code)
        except ValueError:
            code = 1

        sys.stderr.write('{0}\n'.format(message))
        sys.exit(code)

    def fail(self, code=1, exit=True):
        """Write ERROR and exit with specified code

        Write ERROR message to screen and exit with specified exit code

        """
        try:
            code = int(code)
        except ValueError:
            code = 1

        self.message('ERROR\n')
        if exit:
            sys.exit(code)

    def ok(self, exit=True):
        """Write OK and exit with 0

        Write OK message to screen and exit with 0 exit code

        """
        self.message('OK\n')
        if exit:
            sys.exit(0)

    def message(self, message):
        """Write message to stdout

        Write specified message to stdout

        """
        sys.stdout.write('{0}'.format(message))

    @property
    def pid(self):
        """Return PID from pidfile

        Read the PID file and return PID found in the file

        """
        if not os.path.isfile(self.pidfile):
            logger.debug('No such file: {0̋'.format(self.pidfile))
            return False

        if not os.access(self.pidfile, os.R_OK):
            logger.debug('Not readable: {0}'.format(self.pidfile))
            return False

        p = Popen(['pgrep', '-F', self.pidfile], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        (stdout,sterr) = p.communicate()
        if p.returncode != 0:
            return None

        try:
            return int(stdout.strip())
        except ValueError:
            raise InitScriptError('invalid pidfile contents: {0}'.format(pidfile))

    @property
    def is_running(self):
        """Check if service is running

        Returns True, if pidfile is specified and pgreg -F finds the process

        """
        if not os.path.isfile(self.pidfile):
            logger.debug('No such file: {0}'.format(self.pidfile))
            return False

        if not os.access(self.pidfile, os.R_OK):
            logger.debug('Not readable: {0}'.format(self.pidfile))
            return False

        p = Popen(['pgrep', '-F', self.pidfile], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()
        return p.returncode == 0

    def parse_args(self):
        """Parse arguments
        """
        args = self.parser.parse_args()
        if args.debug:
            logging.basicConfig(level=logging.DEBUG, format=LOGGING_FORMAT, datefmt=LOGGING_TIME_FORMAT)

        return args

    def status(self):
        """
        """
        if self.is_running:
            self.message('Running: {0} (pid {1})\n'.format((self.name, self.pid)))
        else:
            self.message('Not running: {0}\n'.format(self.name))

    def stop(self, exit=True):
        """Stop service

        Stop the service if PID file was not found

        """
        if not self.is_running:
            raise InitScriptError('{0}: not running'.format(self.name))

        self.message('Stopping: {0} (pid {1}) '.format(self.name, self.pid))
        command = ['pkill', '-F', self.pidfile]
        p = Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()

        if p.returncode != 0:
            self.fail(p.returncode, exit=exit)
        self.ok(exit=exit)

    def start(self):
        """Start service

        Start the service if PID file was not found

        """
        if self.is_running:
            self.error('{0}: already running (pid {1})'.format(self.name, self.pid))

        if not os.access(self.daemon, os.X_OK):
            self.error('Not executable: {0}'.format(self.daemon))

        self.message('Starting: {0} '.format(self.name))
        command = [self.daemon] + self.daemon_args
        p = Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()
        if p.returncode != 0:
            self.fail(p.returncode)
        self.ok()

    def restart(self):
        """Attempt to restart the service

        Attempt to stop and start the service

        """
        try:
            self.stop(exit=False)
        except InitScriptError:
            pass

        self.start()

    def run(self):
        """Run init script

        Parse command line arguments and execute given command

        """

        args = self.parse_args()
        try:
            callback = getattr(self, args.command)
            if callback is None:
                raise AttributeError
        except AttributeError:
            self.error(code=1, message='Function not implemented: {0}'.format(args.command))

        try:
            return callback()
        except InitScriptError as e:
            self.error(code=1, message=e)
