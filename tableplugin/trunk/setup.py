#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2013 Jonny Weir <jonnyweir@jonnyweir.entadsl.com>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from setuptools import setup

PACKAGE = 'TablePlugin'
VERSION = 0.2

setup(name=PACKAGE,
      version=VERSION,
      author="Jonny Weir",
      author_email="jonnyweir@jonnyweir.entadsl.com",
      license="BSD 3-Clause",
      packages=['table'],
      entry_points="""
      [trac.plugins]
      table = table
      """,
)
