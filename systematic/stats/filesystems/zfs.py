"""
ZFS pool / volume status
"""

import json

from systematic.filesystems.zfs.zfs import ZfsClient
from systematic.filesystems.zfs.zpool import ZPoolClient
from systematic.stats import StatsParser, StatsParserError
from systematic.platform import JSONEncoder

class ZFSStats(StatsParser):
    """ZFS status

    Combined ZFS zpool and zfs status parser
    """
    parser_name = 'zfs'
    json_encoder = JSONEncoder

    def __init__(self):
        super(ZFSStats, self).__init__()
        self.zpool_client = ZPoolClient()
        self.zfs_client = ZfsClient()

    @property
    def zpools(self):
        """Return zpools

        """
        return self.zpool_client.zpools

    @property
    def volumes(self):
        """Return zfs volumes

        """
        return self.zfs_client.volumes

    @property
    def snapshots(self):
        """Return zfs snapshots

        """
        return self.zfs_client.snapshots

    def update(self):
        """Update data

        """
        self.zpool_client.load_zpools()
        self.zfs_client.load_volumes()
        self.zfs_client.load_snapshots()
        return self.update_timestamp()

    def to_json(self, verbose=False):
        """Return JSON data

        """
        return json.dumps(
            {
                'timestamp': self.__updated__,
                'zpools': [zpool.as_dict(verbose=verbose) for zpool in self.zpools],
                'volumes': [volume.as_dict(verbose=verbose) for volume in self.volumes],
                'snapshots': [snapshot.as_dict(verbose=verbose) for snapshot in self.snapshots],
            },
            indent=2,
            cls=self.json_encoder,
        )
