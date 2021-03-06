#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
import os

from setuptools import setup

setup(
    name = 'TracIrresistibleTheme',
    version = '1.0',
    packages = ['irresistibletheme'],
    package_data = {'irresistibletheme': ['templates/*.html', 'htdocs/*.js', 'htdocs/*.css']},

    author = 'Noah Kantrowitz',
    author_email = 'noah@coderanger.net',
    description = '',
    long_description = open(os.path.join(os.path.dirname(__file__), 'README')).read(),
    license = 'GPL',
    keywords = 'trac theme',
    url = 'http://trac-hacks.org/wiki/IrresistibleTheme',
    download_url = 'http://trac-hacks.org/svn/irresistibletheme/0.11#egg=TracIrresistibleTheme-dev',
    classifiers = [
        'Framework :: Trac',
        #'Development Status :: 1 - Planning',
        # 'Development Status :: 2 - Pre-Alpha',
         'Development Status :: 3 - Alpha',
        # 'Development Status :: 4 - Beta',
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        'Environment :: Web Environment',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    
    install_requires = ['Trac', 'TracThemeEngine'],

    entry_points = {
        'trac.plugins': [
            'irresistibletheme.theme = irresistibletheme.theme',
        ]
    },
)
