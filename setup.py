#!/usr/bin/env python
"""
Package setup script for easy_install
"""

import sys,os
from setuptools import setup

VERSION='1.4.1'
README = open(os.path.join(os.path.dirname(__file__),'README.txt'),'r').read()

platform_packages = []
platform_deps = []
if sys.platform == 'darwin':
    platform_packages.extend(['systematic/darwin'])
    platform_deps.extend(['appscript','pyfsevents'])

setup(
    name = 'systematic',
    version = VERSION,
    license = 'PSF',
    keywords = 'System Management Utility Classes Scripts',
    url = 'http://tuohela.net/packages/systematic',
    zip_safe = False,
    packages = ['systematic','systematic.logs'] + platform_packages,
    package_dirs = {'systematic': 'systematic'},
    install_requires = [ 'setproctitle', 'lxml','configobj', 'seine' ] + platform_deps,
    author = 'Ilkka Tuohela', 
    author_email = 'hile@iki.fi',
    description = 'Sysadmin utility classes and scripts',
    long_description = README, requires=['systematic'],

)   

