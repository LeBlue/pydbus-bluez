#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from os import path
import re

here = path.abspath(path.dirname(__file__))

pkgname = 'pydbusbluez'
src_dir = 'src'

def find_version(*file_paths):
    with open(path.join(here, *file_paths), encoding='utf-8') as f:
        version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')

def long_description(*file_paths):
    with open(path.join(here, *file_paths), encoding='utf-8') as f:
        return f.read()


setup(
   name=pkgname,
   version=find_version(src_dir, pkgname, '__init__.py'),
   description='Utils for testing and configuration of ble devices via bluez dbus API',
   author='Matthias Wauer',
   author_email='matthiaswauer@gmail.com',
   packages=find_packages(where=src_dir),
   package_dir={
      '': src_dir,
   },
   url='https://github.com/LeBlue/pydbus-bluez',

   install_requires=[
      'simplejson',
      'pydbus;platform_system=="Linux"'
   ], #external packages as dependencies
   include_package_data=True,
   license='MIT',
   classifiers=[
      'Development Status :: 4 - Beta',
      'Environment :: Console',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Operating System :: Linux',
      'Programming Language :: Python :: 3.5',
      'Programming Language :: Python :: 3.6',
      'Programming Language :: Python :: 3.7',
      'Topic :: Software Development :: Testing',
   ],
   entry_points={
      'console_scripts': [
         'pydbus_bluez_dev_info = {}.device_info:main'.format(pkgname),
     ]
   }
)