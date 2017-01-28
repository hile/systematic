"""
Test dmidecode parser
"""

from datetime import datetime
import pytest

from systematic.stats import StatsParserError

def test_dmi_parser(platform_freebsd, platform_linux):
    """Test DMI

    """
    from systematic.stats.hardware.dmi import DMI, DMITable, DMIHandle, DMIProperty
    dmi = DMI()

    assert dmi.version == None
    assert dmi.updated == None
    assert dmi.tables == []

    dmi.update()
    assert isinstance(dmi.version, str) or isinstance(dmi.version, unicode)
    assert isinstance(dmi.updated, float)

    assert len(dmi.tables) > 0
    for table in dmi.tables:
        assert isinstance(table, DMITable)

        assert isinstance(table.address, unicode)
        int(table.address, 16)
        assert len(table.handles) > 0

        for handle in table.handles:
            assert isinstance(handle, DMIHandle)
            assert handle.table == table

            assert isinstance(handle.name, unicode)
            assert isinstance(handle.offset, int)
            assert isinstance(handle.handle_type, int)
            assert isinstance(handle.handle_bytes, int)

            for prop in handle.properties:
                assert isinstance(prop, DMIProperty)
                assert isinstance(prop.name, unicode)
                assert isinstance(prop.value, unicode)

                for option in prop.options:
                    assert isinstance(option, unicode)
