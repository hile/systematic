"""
Test zpool status parsers
"""
from __future__ import unicode_literals

import pytest
import sys

from builtins import str

TEST_ZPOOL_COUNT = 2

SUPPORTED_PLATFORMS = (
    'freebsd10',
    'freebsd11',
)


@pytest.mark.skipif(sys.platform not in SUPPORTED_PLATFORMS, reason='Platform not supported')
def test_zpool_list(platform_mock_binaries):
    from systematic.filesystems.zfs import ZPoolClient
    client = ZPoolClient()
    client.load_zpools()
    assert len(client.zpools) == TEST_ZPOOL_COUNT

    for zpool in client.zpools:
        assert isinstance(zpool.name, str)
        assert isinstance(zpool.health, str)
        assert isinstance(zpool.altroot, str)
        assert isinstance(zpool.used_gb, str)
        assert isinstance(zpool.available_gb, str)

        assert isinstance(zpool.available, int)
        assert isinstance(zpool.used, int)
        assert isinstance(zpool.size, int)
        assert isinstance(zpool.capacity, int)
        assert isinstance(zpool.fragmentation, int)

        assert isinstance(zpool.deduplication, float)

        assert isinstance(zpool.as_dict(), dict)

        assert zpool.size == zpool.available + zpool.used
