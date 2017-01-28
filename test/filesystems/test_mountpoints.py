"""
Test filesystem mountpoints
"""

from datetime import datetime

import json
import pytest

def test_mountpoint_attributes(platform_darwin, platform_freebsd, platform_linux):
    """Test mountpoint attributes

    """

    from systematic.filesystems import MountPoints
    from systematic.classes import MountPoint

    mounts = MountPoints()
    assert len(mounts) > 0

    for mp in mounts:
        assert isinstance(mp, MountPoint)

        assert isinstance(mp.path, unicode)
        assert isinstance(mp.name, unicode)

        assert isinstance(mp.usage, dict)
        assert isinstance(mp.flags, dict)

        assert isinstance(mp.size, int)
        assert isinstance(mp.used, int)
        assert isinstance(mp.available, int)
        assert isinstance(mp.free, int)
        assert isinstance(mp.percent, int)

        if platform_darwin:
            assert isinstance(mp.blocksize, int)
            assert isinstance(mp.internal, bool)
            assert isinstance(mp.writable, bool)
            assert isinstance(mp.bootable, bool)
            assert isinstance(mp.ejectable, bool)
            assert isinstance(mp.removable, bool)

        assert isinstance(mp.as_dict(), dict)
        json.dumps(mp.as_dict())

def test_mountpoint_sorting(platform_darwin, platform_freebsd, platform_linux):
    """Test sorting of mountpoints

    """
    from systematic.filesystems import MountPoints
    mounts = MountPoints()

    values = sorted(mp for mp in mounts)
    assert len(values) == len(mounts)

    mounts.sort()
    for i, mp in enumerate(mounts):
        assert mp == values[i]

