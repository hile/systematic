"""
Unit tests for module imports
"""

import warnings
import pytest

def test_dmi_import(capsys):
    """Test legacy systematic.dmi

    """
    with pytest.warns(FutureWarning):
        from systematic.dmi import *


def test_smart_import(capsys):
    """Test legacy systematic.smart

    """
    with pytest.warns(FutureWarning):
        from systematic.smart import *

