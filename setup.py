#!/usr/bin/env python

from distutils.core import setup

setup(
    name='randrctl',
    version='0.1',
    url='http://github.com/edio/randrctl',
    license='GPLv3',
    author='Dmytro Kostiuchenko',
    author_email='edio@archlinux.us',
    description='Profile based screen manager for X',
    packages=['randrctl'],
    scripts=['bin/randrctl']
)
