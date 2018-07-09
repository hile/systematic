"""
SMART Compatibility import for old module path

Use systematic.stats.hardware.dmi in new code
"""

from warnings import warn
from systematic.stats.hardware.dmi import *  # noqa

warn('Warning: systematic.dmi is deprecated. Use systematic.stats.hardware.dmi', FutureWarning)
