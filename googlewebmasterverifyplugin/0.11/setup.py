#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

__url__      = ur"$URL$"[6:-2]
__author__   = ur"$Author$"[9:-2]
__revision__ = int("0" + ur"$Rev$"[6:-2])
__date__     = ur"$Date$"[7:-2]



setup(
    name = 'TracGoogleWebmasterVerifyPlugin',
    version = '0.2',
    packages = ['tracgooglewebmasterverify'],
    author = 'Martin Scharrer',
    author_email = 'martin@scharrer-online.de',
    description = "GoogleWebmasterVerify Plugin for Trac",
    url = 'http://www.trac-hacks.org/wiki/GoogleWebmasterVerifyPlugin',
    license      = 'GPLv3',
    zip_safe     = False,
    keywords = 'trac google webmaster verify wiki plugin',
    classifiers = ['Framework :: Trac'],
    entry_points = {'trac.plugins': ['tracgooglewebmasterverify.plugin = tracgooglewebmasterverify.plugin']}
)

