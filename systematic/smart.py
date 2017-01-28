"""
Compatibility import for old path

Use systematic.stats.hardware.smart in new code
"""

from warnings import warn
warn('Warning: systematic.smart is deprecated. Use systematic.stats.hardware.smart', FutureWarning)

from systematic.stats.hardware.smart import *
