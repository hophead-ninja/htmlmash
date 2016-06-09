from __future__ import print_function
import sys
from distutils.core import setup

if sys.version < "3.4":
    print('Python >= 3.4 is required')
    exit(1)

setup(
    name='htmlmash',
    version='0.1.0',
    description='Objective html templates',
    packages=['htmlmash'],
    license='BSD',
    author='Dawid Czech'
)
