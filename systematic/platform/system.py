
import fnmatch
import sys


class SystemInformation:
    """
    Return platform specific system information
    """

    def __init__(self):
        if sys.platform[:5] == 'linux':
            from systematic.platform.linux.system import SystemInformation as loader

        elif sys.platform == 'darwin':
            from systematic.platform.darwin.system import SystemInformation as loader

        elif fnmatch.fnmatch(sys.platform, 'freebsd*'):
            from systematic.platform.bsd.system import SystemInformation as loader

        else:
            raise NotImplementedError('Syste knformationloader for OS not available: {0}'.format(sys.platform))

        self.loader = loader()

    def __getattr__(self, attr):
        return getattr(self.loader, attr)
