"""
Unit tests for filesystem mount parsing code
"""

import sys
import unittest

from systematic.filesystems import MountPoints, MountPoint, FileSystemError

class test_filesystems(unittest.TestCase):
    """
    Test the mount point parsing code
    """

    def test1_list_mountpoints(self):

        """
        Test listing mount points on this platform
        """
        try:
            mp = MountPoints()
            self.assertIsInstance(mp.keys(), list)
        except FileSystemError, emsg:
            print emsg
            return

    def test2_check_mounpoint_type(self):
        """
        Check object type of returned filesystems
        """
        try:
            mp = MountPoints()
        except FileSystemError, emsg:
            print emsg
            return

        if sys.platform=='windows':
            # TODO - implement windows tests
            pass
        else:
            rootfs = mp['/']
            self.assertIsInstance(rootfs, MountPoint)

