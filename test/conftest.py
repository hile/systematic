"""
Platform fixtures
"""

import os
import pytest

TEST_PLATFORMS = (
    'darwin',
    'linux',
    'freebsd',
)

def platform_mock_binaries(request, platform):
    """Test for supported platforms

    Setup OS platform mock PATH: allows running deterministic commands to mock
    output of system commands with subprocess.Popen transparently.
    """
    mockroot = 'test/tools/mock/{0}'.format(platform)
    assert os.path.isdir(mockroot)
    os.environ['PATH'] = os.pathsep.join([os.path.join(mockroot, 'bin'), os.environ.get('PATH')])
    return platform

@pytest.fixture(scope='module')
def platform_openbsd(request):
    return platform_mock_binaries(request, 'openbsd')

@pytest.fixture(scope='module')
def platform_freebsd(request):
    return platform_mock_binaries(request, 'freebsd')

@pytest.fixture(scope='module')
def platform_linux(request):
    return platform_mock_binaries(request, 'linux')

@pytest.fixture(scope='module')
def platform_darwin(request):
    return platform_mock_binaries(request, 'darwin')
