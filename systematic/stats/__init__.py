"""
Status monitors and counters for various programs
"""

import time

from systematic.shell import ShellCommandParser, ShellCommandParserError


class StatsParserError(Exception):
    pass


class StatsParser(ShellCommandParser):
    """Common class for stats parser

    """
    parser_name = 'unknown'

    def __init__(self, *args, **kwargs):
        super(StatsParser, self).__init__()
        self.__updated__ = None

    def __repr__(self):
        return '{0} stats'.format(self.parser_name)

    def execute(self, *args, **kwargs):
        """Wrap execute calls

        Wrap execute calls and replace ShellCommandParserError with StatsParserError
        """
        try:
            return super(StatsParser, self).execute(*args, **kwargs)
        except ShellCommandParserError as e:
            raise StatsParserError(e)

    def update_timestamp(self):
        """Update timestamp

        Update self.__updated__
        """
        self.__updated__ = float(time.time())
        return self.__updated__
