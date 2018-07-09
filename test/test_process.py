"""
Test systematic.process module
"""

from builtins import str
from datetime import datetime


def test_ps_fields():
    """Test PS_FIELDS

    Test PS_FIELDS array contents
    """
    from systematic.process import PS_FIELDS
    assert isinstance(PS_FIELDS, tuple)
    for key in PS_FIELDS:
        assert isinstance(key, str)


def test_processes(platform_mock_binaries):
    from systematic.process import Processes, Process
    ps = Processes()
    assert len(ps) > 0

    for process in ps:
        assert isinstance(process, Process)
        assert isinstance(process.started, datetime)

        for attr in ('command', 'ruser', 'state', 'time', 'tdev'):
            value = getattr(process, attr)
            assert isinstance(value,  str), 'Attribute {0} value {1} is not string: {2}'.format(
                attr,
                value,
                type(value)
            )

        for attr in ('pid', 'ppid', 'ruid', 'rgid', 'rss', 'vsz'):
            value = getattr(process, attr)
            assert isinstance(value, int)
