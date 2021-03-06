#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from setuptools import setup

setup(
    name = 'TracWikiwyg',
    version = '1.0',
    packages = ['wikiwyg'],
    package_data = {'wikiwyg': ['htdocs/*.js', 'htdocs/*.css', 'htdocs/*.gif', 'htdocs/*.htc', 'templates/*.js']},
    
    author = "soloturn, Erik Rose, and Frank Wierzbicki",
    author_email = "somebody@example.com",
    description = "Add a WYSIWYG wiki editor to Trac.",
    long_description = "Gives Trac a WYSIWYG editor which outputs nice WikiFormatting rather than HTML, care of the Wikiwyg library.",
    license = "LGPL",
    keywords = "trac plugin wiki wysiwyg wikiwyg editor",
    url = "http://trac-hacks.org/wiki/WikiWygPlugin",
    classifiers = [
        'Framework :: Trac',
    ],
    
    entry_points = {
        'trac.plugins': [
            'wikiwyg.web_ui = wikiwyg.web_ui'
        ]
    }
)
