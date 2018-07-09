"""
Network services by lsof
"""

import json

from systematic.stats import StatsParser

LSOF_FIELDS = (
    'command',
    'pid',
    'user',
    'fd',
    'connection_type',
    'device',
    'offset',
    'node',
    'name',
)


class LsofStatEntry(dict):
    """Entry from LsofStats

    """
    def __init__(self, command, pid, user, fd, connection_type, device, offset, node, name):
        self.update(
            command=command,
            pid=int(pid),
            user=user,
            fd=fd,
            connection_type=connection_type,
            device=device,
            offset=offset,
            node=node,
            name=name,
        )


class LsofStats(StatsParser):
    """Parse lsof output

    Parse output of lsof -nPi command
    """
    parser_name = 'lsof -nPi'

    def update(self):
        """Update stats

        """
        self.stats = []
        stdout, stderr = self.execute(('lsof', '+c0', '-nPi', ))
        for line in stdout.splitlines()[1:]:
            fields = line.split(None, len(LSOF_FIELDS) - 1)
            entry = LsofStatEntry(**dict((key, fields[i]) for i, key in enumerate(LSOF_FIELDS)))
            self.stats.append(entry)
        self.update_timestamp()

    def as_dict(self, verbose=False):
        """Show results as JSON

        """
        if self.__updated__ is None:
            self.update()
        return {
            'timestamp': self.__updated__,
            'stats': self.stats,
        }

    def to_json(self, verbose=False):
        return json.dumps(self.as_dict(verbose), indent=2)
