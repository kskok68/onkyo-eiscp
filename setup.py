#!/usr/bin/env python
# coding: utf8

from setuptools import setup, find_packages

# Get long_description from README
import os
here = os.path.dirname(os.path.abspath(__file__))
f = open(os.path.join(here, 'README.rst'))
long_description = f.read().strip()
f.close()

lib_folder = os.path.dirname(os.path.realpath(__file__))
requirement_path = f"{lib_folder}/requirements.txt"
install_requires = []
if os.path.isfile(requirement_path):
    with open(requirement_path) as f:
        install_requires = f.read().splitlines()
setup(
    name='onkyo-eiscp',
    version='1.5.3',
    url='https://github.com/mitchcapper/onkyo-eiscp',
    license='MIT',
    author='Michael Elsdörfer',
    author_email='michael@elsdoerfer.com',
    description='Control Onkyo receivers over ethernet.',
    long_description=long_description,
    packages = find_packages(exclude=('tests*',)),
    entry_points="""[console_scripts]\nonkyo = eiscp.script:run\n""",
    install_requires=install_requires,
    platforms='any',
    classifiers=[
        'Topic :: System :: Networking',
        'Topic :: Games/Entertainment',
        'Topic :: Multimedia',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
