"""
Wrapper for running rsync commands from python
"""

import time
from subprocess import Popen,PIPE

from systematic.shell import CommandPathCache
from systematic.log import Logger,LoggerError

DEFAULT_RSYNC_FLAGS = [
    '-av',
    '--delete',
    '--progress',
    '--exclude=.Apple*',
    '--exclude=.DS_Store',
    '--exclude=.DocumentRevisions-V100',
    '--exclude=.Spotlight-V100',
    '--exclude=.Trashes',
    '--exclude=.fseventsd',
]

DEFAULT_OUTPUT_FORMAT = '--out-format="%t %o:%f %b"'

class RsyncError(Exception):
    """
    Exceptions raised when running rsync commands
    """
    def __str__(self):
        return self.args[0]

class RsyncCommand(object):
    """
    Wrapper to execute rsync to target nicely from python
    """
    def __init__(self,src,dst,flags=DEFAULT_RSYNC_FLAGS,output_format=DEFAULT_OUTPUT_FORMAT):
        self.log = Logger('rsync').default_stream
        self.src = src
        self.dst = dst
        self.flags = flags
        self.output_format = output_format

        cmd = CommandPathCache().which('rsync')
        if cmd is None:
            raise RsyncError('No such command: rsync')
        self.command = [cmd] + flags + [ self.output_format, '{0}'.format(src),'{0}'.format(dst) ]

    def __str__(self):
        return ' '.join(self.command)

    def run(self,verbose=False):
        """
        Run the rsync command specific in __init__()
        """
        if not verbose and self.log.level == logging.DEBUG:
            verbose = True
        try:
            p = Popen(self.command,stdin=PIPE,stdout=PIPE,stderr=PIPE)
            self.log.debug('Running: {0}'.format(self))

            rval = None
            while rval is None:
                if verbose:
                    while True:
                        l = p.stdout.readline()
                        if l == '':
                            break
                        sys.stdout.write('{0}\n'.format(l.rstrip()))
                time.sleep(0.2)
                rval = p.poll()

            self.log.debug('Return code: {0}'.format(rval))
            if rval != 0:
                raise RsyncError('Error running command {0}: {1}'.format(self,p.stderr.read()))

        except KeyboardInterrupt:
            self.log.debug('Rsync interrupted')
            raise KeyboardInterrupt
