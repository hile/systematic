#!/usr/bin/env python
"""
Package setup script for easy_install
"""

import sys,os
from setuptools import setup

VERSION='1.4.1'
README = open(os.path.join(os.path.dirname(__file__),'README.txt'),'r').read()

packages = ['systematic','systematic.logs']
package_dirs = {'systematic': 'systematic'}
deps = [ 'setproctitle', 'lxml','configobj', 'seine' ]

if sys.platform == 'darwin':
    packages.append('systematic/darwin')
    deps.append('appscript')

setup(
    name = 'systematic',
    version = VERSION,
    license = 'PSF',
    keywords = 'System Management Utility Classes Scripts',
    url = 'http://tuohela.net/packages/systematic',
    zip_safe = False,
    packages = packages,
    package_dirs = package_dirs,
    install_requires = deps,
    author = 'Ilkka Tuohela', 
    author_email = 'hile@iki.fi',
    description = 'Sysadmin utility classes and scripts',
    long_description = README,

)   

