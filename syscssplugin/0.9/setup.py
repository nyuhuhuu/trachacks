#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from setuptools import setup

setup(
    name = 'SysCss',
    version = '0.1',
    packages = ['syscss'],

    author = "Noah Kantrowitz",
    author_email = "noah@coderanger.net",
    description = "Provides a system-wide CSS file for Trac",
    license = "BSD",
    keywords = "trac system css",
    url = "http://trac-hacks.org",
    
    entry_points = {
        'trac.plugins': [
            'syscss.syscss = syscss.syscss'
        ]
    }
)
