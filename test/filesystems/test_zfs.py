"""
Test zfs volume/snapshot status parsers
"""
from __future__ import unicode_literals

import pytest
import sys

from builtins import str

TEST_ZPOOL_COUNT = 2
TEST_VOLUME_COUNT = 14
TEST_SNAPSHOT_COUNT = 2

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


@pytest.mark.skipif(sys.platform not in SUPPORTED_PLATFORMS, reason='Platform not supported')
def test_zfs_list(platform_mock_binaries):
    from systematic.filesystems.zfs import ZfsClient
    client = ZfsClient()

    client.load_volumes()
    assert len(client.volumes) == TEST_VOLUME_COUNT

    for volume in client.volumes:
        assert isinstance(volume.name, str)
        assert isinstance(volume.fstype, str)
        assert isinstance(volume.used_gb, str)
        assert isinstance(volume.available_gb, str)

        assert isinstance(volume.available, int)
        assert isinstance(volume.used, int)

        assert isinstance(volume.as_dict(), dict)

    client.load_snapshots()
    assert len(client.snapshots) == TEST_SNAPSHOT_COUNT

    for snapshot in client.snapshots:
        assert isinstance(snapshot.name, str)
        assert isinstance(snapshot.volume, str)

        assert isinstance(snapshot.fstype, str)

        assert isinstance(snapshot.as_dict(), dict)
