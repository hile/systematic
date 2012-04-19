"""
Unit test tests for systematic
"""

import os

#noinspection PyUnresolvedReferences
__all__ = filter(lambda x:
    x[:5]=='test_' and os.path.splitext(x)[1]=='.py',
    os.listdir(os.path.dirname(__file__))
)
