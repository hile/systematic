
import glob
from setuptools import setup, find_packages
from systematic import __version__

setup(
    name = 'systematic',
    keywords = 'system management utility scripts',
    description = 'Sysadmin utility classes and scripts',
    author = 'Ilkka Tuohela',
    author_email = 'hile@iki.fi',
    url = 'https://github.com/hile/systematic/',
    version = __version__,
    license = 'PSF',
    packages = find_packages(),
    scripts = glob.glob('bin/*'),
    install_requires = (
        'configobj',
    ),
    setup_requires = (
        'pytest-runner',
    ),
    tests_require = (
        'pytest',
        'pytest-datafiles',
    ),
)
