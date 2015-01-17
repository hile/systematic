#!/usr/bin/env python
"""
Platform indepependent tools for sysadmins.

Platform dependent modules are now split to their own packages.
"""

import sys
import os
from setuptools import setup, find_packages

VERSION='4.2.3'

setup(
    name = 'systematic',
    keywords = 'system management utility scripts',
    description = 'Sysadmin utility classes and scripts',
    author = 'Ilkka Tuohela',
    author_email = 'hile@iki.fi',
    url = 'http://tuohela.net/packages/systematic',
    version = VERSION,
    license = 'PSF',
    zip_safe = False,
    packages = find_packages(),
    install_requires = (
        'setproctitle',
        'configobj',
    ),
)

