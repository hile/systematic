"""
SMART Compatibility import for old module path

Use systematic.stats.hardware.dmi in new code
"""

from warnings import warn
warn('Warning: systematic.dmi is deprecated. Use systematic.stats.hardware.dmi', FutureWarning)

from systematic.stats.hardware.dmi import *
