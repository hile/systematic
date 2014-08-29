#!/usr/bin/env python
"""
Platform indepependent tools for sysadmins.

Platform dependent modules are now split to their own packages.
"""

import sys
import os
from setuptools import setup

VERSION='4.0.7'
README = open(os.path.join(os.path.dirname(__file__),'README.md'),'r').read()

setup(
    name = 'systematic',
    keywords = 'system management utility scripts',
    description = 'Sysadmin utility classes and scripts',
    long_description = README,
    author = 'Ilkka Tuohela',
    author_email = 'hile@iki.fi',
    url = 'http://tuohela.net/packages/systematic',
    version = VERSION,
    license = 'PSF',
    zip_safe = False,
    packages = (
        'systematic',
    ),
    install_requires = (
        'setproctitle',
        'configobj',
    ),
)

