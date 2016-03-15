#!/usr/bin/env python

from setuptools import setup, find_packages
import randrctl

version = randrctl.__version__

setup(setup_requires='packit', packit=True)
