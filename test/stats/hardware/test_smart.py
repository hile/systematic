"""
Test smartctl status parser
"""

from datetime import datetime
import pytest

from systematic.stats import StatsParserError

TEST_UNSUPPORTED_DEVICES = (
    '/dev/ses0',
)

def test_smartctl_parser(platform_freebsd): #, platform_linux):
    """Test DMI

    Test smart data parser contents
    """
    from systematic.stats.hardware.smart import SmartCtlClient, SmartDrive, SmartAttribute, SmartInfoField

    client = SmartCtlClient()
    assert len(client.drives) == 0

    client.update()
    assert len(client.drives) == 4

    for drive in client.drives:
        assert isinstance(drive, SmartDrive)
        assert drive.client == client

        assert isinstance(drive.device, unicode)
        assert isinstance(drive.name, unicode)
        assert isinstance(drive.flags, list)

        # Test for unsupported devices as well

        if drive.device not in TEST_UNSUPPORTED_DEVICES:
            assert drive.is_supported == True
            assert drive.is_healthy == True

            attributes = drive.get_attributes()
            assert isinstance(attributes, dict)
            for key, attr in attributes.items():
                assert attr.drive == drive

                assert isinstance(attr, SmartAttribute)
                assert isinstance(attr.description, unicode)

                assert isinstance(attr.items(), list)
                for key, value in attr.items():
                    if key in ( 'updated', 'type', ):
                        assert isinstance(value, unicode)
                    elif key in ( 'failed', ):
                        assert isinstance(value, bool)
                    else:
                        assert isinstance(value, int)

        else:
            assert drive.is_supported == False
            assert drive.is_healthy == False

