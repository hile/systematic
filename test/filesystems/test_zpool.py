"""
Test zpool status parsers
"""

import json
import pytest
import sys

from datetime import datetime

TEST_ZPOOL_COUNT = 2

def test_zpool_list(platform_freebsd):
    from systematic.filesystems.zfs import ZPoolClient
    client = ZPoolClient()
    client.load_zpools()
    assert len(client.zpools) == TEST_ZPOOL_COUNT

    for zpool in client.zpools:
        assert isinstance(zpool.name, unicode)
        assert isinstance(zpool.health, unicode)
        assert isinstance(zpool.altroot, unicode)
        assert isinstance(zpool.used_gb, unicode)
        assert isinstance(zpool.available_gb, unicode)

        assert isinstance(zpool.available, int)
        assert isinstance(zpool.used, int)
        assert isinstance(zpool.size, int)
        assert isinstance(zpool.capacity, int)
        assert isinstance(zpool.fragmentation, int)

        assert isinstance(zpool.deduplication, float)

        assert isinstance(zpool.as_dict(), dict)

        assert zpool.size == zpool.available + zpool.used
