"""
System statistics - vmstat / iostat etc.

Loads platform specific implementations transparently.
"""

import fnmatch
import json
import sys


class SystemStatistics(object):
    """Loader for OS specific system statistics
    """

    def __init__(self):
        if sys.platform[:5] == 'linux':
            from systematic.platform.linux.stats import LinuxSystemStats
            self.loader = LinuxSystemStats()

        elif sys.platform == 'darwin':
            from systematic.platform.darwin.stats import DarwinSystemStats
            self.loader = DarwinSystemStats()

        elif fnmatch.fnmatch(sys.platform, 'freebsd*'):
            from systematic.platform.bsd.stats import BSDSystemStats
            self.loader = BSDSystemStats()

    def update(self):
        """Update counters

        """
        self.loader.update()

    def to_json(self, verbose=False):
        """Return counters as JSON

        """
        return self.loader.to_json(verbose=verbose)
