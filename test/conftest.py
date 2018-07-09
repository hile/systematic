"""
Platform fixtures
"""

import os
import pytest
import sys

STATIC_PATH = os.environ.get('PATH')


@pytest.fixture(scope='module')
def platform_mock_binaries(request):
    """Test for supported platforms

    Setup OS platform mock PATH: allows running deterministic commands
    to mock output of system commands with subprocess.Popen transparently.
    """

    if sys.platform in ('linux', 'linux2'):
        platform = 'linux'
    elif sys.platform in ('freebsd10', 'freebsd11'):
        platform = 'freebsd'
    elif sys.platform in ('darwin'):
        platform = 'darwin'
    else:
        platform = None

    assert platform is not None, 'Unsupported platform: {}'.format(sys.platform)
    mockroot = 'test/tools/mock/{0}'.format(platform)
    assert os.path.isdir(mockroot), 'Mock binaries not found for {}'.format(platform)
    os.environ['PATH'] = os.pathsep.join([os.path.join(mockroot, 'bin'), STATIC_PATH])
