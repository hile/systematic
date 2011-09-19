#!/usr/bin/env python

import os,glob
from setuptools import setup,find_packages

VERSION='1.2'
README = open(os.path.join(os.path.dirname(__file__),'README.txt'),'r').read()

setup(
    name = 'systematic',
    version = VERSION,
    license = 'PSF',
    keywords = 'System Management Utility Classes Scripts',
    url = 'https://github.com/hile/musa/downloads',
    zip_safe = False,
    install_requires = [ 'setproctitle', 'lxml','configobj', 'seine', ],
    scripts = glob.glob('bin/*'),
    packages = ['systematic','systematic.logs'],
    author = 'Ilkka Tuohela', 
    author_email = 'hile@iki.fi',
    description = 'Sysadmin utility classes and scripts',
    long_description = README,

)   

