"""
Test zfs volume/snapshot status parsers
"""

import json
import pytest
import sys

if sys.version_info.major == 2:
    strtype = unicode
else:
    strtype = str

from datetime import datetime

TEST_ZPOOL_COUNT = 2
TEST_VOLUME_COUNT = 14
TEST_SNAPSHOT_COUNT = 2

def test_zpool_list(platform_freebsd):
    from systematic.filesystems.zfs import ZPoolClient
    client = ZPoolClient()
    client.load_zpools()
    assert len(client.zpools) == TEST_ZPOOL_COUNT


def test_zfs_list(platform_freebsd):
    from systematic.filesystems.zfs import ZfsClient
    client = ZfsClient()

    client.load_volumes()
    assert len(client.volumes) == TEST_VOLUME_COUNT

    for volume in client.volumes:
        assert isinstance(volume.name, strtype)
        assert isinstance(volume.fstype, strtype)
        assert isinstance(volume.used_gb, strtype)
        assert isinstance(volume.available_gb, strtype)

        assert isinstance(volume.available, int)
        assert isinstance(volume.used, int)

        assert isinstance(volume.as_dict(), dict)

    client.load_snapshots()
    assert len(client.snapshots) == TEST_SNAPSHOT_COUNT

    for snapshot in client.snapshots:
        assert isinstance(snapshot.name, strtype)
        assert isinstance(snapshot.volume, strtype)

        assert isinstance(snapshot.fstype, strtype)

        assert isinstance(snapshot.as_dict(), dict)
