#!/usr/bin/env python

import sys,os,glob
from setuptools import setup,find_packages

VERSION='1.3'
README = open(os.path.join(os.path.dirname(__file__),'README.txt'),'r').read()

packages = ['systematic','systematic.logs']
scripts = glob.glob('bin/*')
if sys.platform == 'darwin':
    packages.append('systematic.osx')
    scripts.extend(glob.glob('osx/*'))

setup(
    name = 'systematic',
    version = VERSION,
    license = 'PSF',
    keywords = 'System Management Utility Classes Scripts',
    url = 'http://tuohela.net/packages/systematic',
    zip_safe = False,
    install_requires = [ 'setproctitle', 'lxml','configobj', 'seine', ],
    scripts = scripts,
    packages = packages,
    author = 'Ilkka Tuohela', 
    author_email = 'hile@iki.fi',
    description = 'Sysadmin utility classes and scripts',
    long_description = README,

)   

