
import glob
from setuptools import setup, find_packages
from systematic import __version__

setup(
    name='systematic',
    keywords='system management utility scripts',
    description='Sysadmin utility classes and scripts',
    author='Ilkka Tuohela',
    author_email='hile@iki.fi',
    url='https://github.com/hile/systematic/',
    version=__version__,
    license='PSF',
    packages=find_packages(),
    scripts=glob.glob('bin/*'),
    install_requires=(
        'configobj',
        'future',
    ),
    tests_require=(
        'pytest',
        'pytest-runner',
        'pytest-datafiles',
    ),
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Python Software Foundation License',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: System',
        'Topic :: System :: Systems Administration',
    ],
)
