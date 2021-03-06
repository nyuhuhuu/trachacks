#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

__url__      = ur"$URL$"[6:-2]
__author__   = ur"$Author$"[9:-2]
__revision__ = int("0" + ur"$Rev$"[6:-2])
__date__     = ur"$Date$"[7:-2]


setup(
    name         = 'TracAdvParseArgsPlugin',
    version      = '0.4',
    packages     = ['tracadvparseargs'],
    author       = 'Martin Scharrer',
    author_email = 'martin@scharrer-online.de',
    description  = "Advanced argument parser for Trac macros.",
    url          = 'http://www.trac-hacks.org/wiki/AdvParseArgsPlugin',
    license      = 'GPLv3',
    zip_safe     = False,
    keywords     = 'trac plugin parse argument',
    classifiers  = ['Framework :: Trac'],
    entry_points = {'trac.plugins': [
          'tracadvparseargs.macro     = tracadvparseargs.macro',
          'tracadvparseargs.parseargs = tracadvparseargs.parseargs',
      ]}
)

