#!/usr/bin/env python

import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='graphlayer',
    version='0.2.8',
    description='High-performance library for implementing GraphQL APIs',
    long_description=read("README.rst"),
    author='Michael Williamson',
    author_email='mike@zwobble.org',
    url='http://github.com/mwilliamson/python-graphlayer',
    packages=['graphlayer', 'graphlayer.graphql'],
    keywords="graphql graph join ",
    extras_require={
        "graphql": ["graphql-core-next==1.1.1"],
    },
    license="BSD-2-Clause",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)

