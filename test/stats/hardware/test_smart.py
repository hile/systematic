"""
Test smartctl status parser
"""
from __future__ import unicode_literals

import pytest
import sys

from builtins import int, str

TEST_UNSUPPORTED_DEVICES = (
    '/dev/ses0',
)

SUPPORTED_PLATFORMS = (
    'freebsd10',
    'freebsd11',
)


@pytest.mark.skipif(sys.platform not in SUPPORTED_PLATFORMS, reason='Platform not supported')
def test_smartctl_parser(platform_mock_binaries):
    """Test DMI

    Test smart data parser contents
    """

    from systematic.stats.hardware.smart import SmartCtlClient, SmartDrive, SmartAttribute

    client = SmartCtlClient(load_system_config=False)
    assert len(client.drives) == 0

    client.update()
    assert len(client.drives) > 0

    for drive in client.drives:
        assert isinstance(drive, SmartDrive)
        assert drive.client == client

        assert isinstance(drive.device, str)
        assert isinstance(drive.name, str)
        assert isinstance(drive.flags, list)

        # Test for unsupported devices as well

        if drive.device not in TEST_UNSUPPORTED_DEVICES:
            assert drive.is_supported is True
            assert drive.is_healthy is True

            attributes = drive.get_attributes()
            assert isinstance(attributes, dict)
            for key, attr in attributes.items():
                assert attr.drive == drive

                assert isinstance(attr, SmartAttribute)
                assert isinstance(attr.description, str)

                for key, value in attr.items():
                    if key in ('updated', 'type'):
                        assert isinstance(value, str)
                    elif key in ('failed',):
                        assert isinstance(value, bool)
                    else:
                        assert isinstance(value, int)

        else:
            assert drive.is_supported is False
            assert drive.is_healthy is False
