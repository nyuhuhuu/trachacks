#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name = 'TracCodeReview',
    version = '1.1a',
    packages = ['codereview'],
    package_data = {'codereview': ['templates/*.cs', 'htdocs/*.*', 'htdocs/css/*.*']},
    author = 'Exoweb Ltd.',
    author_email = 'research@exoweb.net',
    maintainer = 'Ryan J Ollos',
    maintainer_email = 'ryano@physiosonics.com',
    description = 'Code review plugin for Trac.',
    license = 'BSD',
    keywords = 'trac plugin code review exoweb',
    url = 'http://contrib.exoweb.net/wiki/CodeReviewPlugin',
    classifiers = ['Framework :: Trac'],
    entry_points = {'trac.plugins': ['codereview = codereview']}
)
