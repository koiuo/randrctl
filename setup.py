#!/usr/bin/env python

from distutils.core import setup
import randrctl

version = randrctl.__version__

setup(
    name='randrctl',
    version=version,
    url='http://github.com/edio/randrctl',
    license='GPLv3',
    author='Dmytro Kostiuchenko',
    author_email='edio@archlinux.us',
    description='Profile based screen manager for X',
    packages=['randrctl'],
    scripts=['bin/randrctl']
)
