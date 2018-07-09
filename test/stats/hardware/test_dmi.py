"""
Test dmidecode parser
"""
from __future__ import unicode_literals

import pytest
import sys

from builtins import int, str  # noqa: 401

SUPPORTED_PLATFORMS = (
    'freebsd10',
    'freebsd11',
    'linux',
    'linux2',
)


@pytest.mark.skipif(sys.platform not in SUPPORTED_PLATFORMS, reason='Platform not supported')
def test_dmi_parser(platform_mock_binaries):
    """Test DMI

    """

    from systematic.stats.hardware.dmi import DMI, DMITable, DMIHandle, DMIProperty
    dmi = DMI()

    assert dmi.version is None
    assert dmi.updated is None
    assert dmi.tables == []

    dmi.update()
    assert isinstance(dmi.version, str)
    assert isinstance(dmi.updated, float)

    assert len(dmi.tables) > 0
    for table in dmi.tables:
        assert isinstance(table, DMITable)

        assert isinstance(table.address, str)
        int(table.address, 16)
        assert len(table.handles) > 0

        for handle in table.handles:
            assert isinstance(handle, DMIHandle)
            assert handle.table == table

            assert isinstance(handle.name, str)
            assert isinstance(handle.offset, int)
            assert isinstance(handle.handle_type, int)
            assert isinstance(handle.handle_bytes, int)

            for prop in handle.properties:
                assert isinstance(prop, DMIProperty)
                assert isinstance(prop.name, str)
                assert isinstance(prop.value, str)

                for option in prop.options:
                    assert isinstance(option, str)
