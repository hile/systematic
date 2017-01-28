"""
Filesystem status parsers
"""

import json

from systematic.filesystems import MountPoints
from systematic.stats import StatsParser, StatsParserError


class FilesystemStatsError(Exception):
    pass


class MountpointStats(StatsParser):
    """Stats for filesystems

    Uses systematic.MountPoints to parse filesystem stats
    """
    parser_name = 'filesystems'

    def __init__(self):
        super(FilesystemStats, self).__init__()
        self.mountpoints = MountPoints()
        self.update_timestamp()

    def update(self):
        """Update filesystems

        """
        self.mountpoints.update()
        return self.update_timestamp()

    def to_json(self, verbose=True):
        """Return JSON data

        """
        if self.__updated__ is None:
            self.update()
        return json.dumps({
                'timestamp': self.__updated__,
                'filesystems': [mp.as_dict(verbose=verbose) for mp in self.mountpoints],
            },
            indent=2,
        )
