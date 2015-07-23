#!/usr/bin/env python
"""
Platform indepependent tools for sysadmins.

Platform dependent modules are now split to their own packages.
"""

import sys
import os
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
    install_requires = (
        'setproctitle',
        'configobj',
    ),
)

