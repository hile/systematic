"""
Test filesystem mountpoints
"""
from __future__ import unicode_literals

from builtins import int, str

import json


def test_mountpoint_attributes(platform_mock_binaries):
    """Test mountpoint attributes

    """

    from systematic.filesystems import MountPoints
    from systematic.classes import MountPoint

    mounts = MountPoints()
    assert len(mounts) > 0

    for mp in mounts:
        assert isinstance(mp, MountPoint)

        assert isinstance(mp.path, str)
        assert isinstance(mp.name, str)

        assert isinstance(mp.usage, dict)
        assert isinstance(mp.flags, dict)

        assert isinstance(mp.size, int)
        assert isinstance(mp.used, int)
        assert isinstance(mp.available, int)
        assert isinstance(mp.free, int)
        assert isinstance(mp.percent, int)

        assert isinstance(mp.as_dict(), dict)
        json.dumps(mp.as_dict())

        # Only available with MacOS (darwin) ps output
        if hasattr(mp, 'blocksize'):
            assert isinstance(mp.blocksize, int)
        for attr in ('internal', 'writable', 'bootable', 'ejectable', 'removable'):
            if hasattr(mp, attr):
                assert isinstance(getattr(mp, attr), bool)


def test_mountpoint_sorting(platform_mock_binaries):
    """Test sorting of mountpoints

    """
    from systematic.filesystems import MountPoints
    mounts = MountPoints()

    values = sorted(mp for mp in mounts)
    assert len(values) == len(mounts)

    mounts.sort()
    for i, mp in enumerate(mounts):
        assert mp == values[i]
