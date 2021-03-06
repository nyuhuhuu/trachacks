# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 daveappendix
# Copyright (C) 2010-2012 Franz Mayer <franz.mayer@gefasoft.de>
#
# "THE BEER-WARE LICENSE" (Revision 42):
# <franz.mayer@gefasoft.de> wrote this file.  As long as you retain this 
# notice you can do whatever you want with this stuff. If we meet some day, 
# and you think this stuff is worth it, you can buy me a beer in return. 
# Franz Mayer
#
# Author: Franz Mayer <franz.mayer@gefasoft.de>

from setuptools import find_packages, setup

# name can be any name.  This name will be used to create the .egg file.
# name that is used in packages is the one that is used in the trac.ini file.
# use package name as entry_points
setup(
    name='Roadmap Plugin', 
    version='0.4.1',
    author = 'Franz Mayer, Gefasoft AG',
    author_email = 'franz.mayer@gefasoft.de', 
    description = 'Sorts roadmap in descending order and adds an filter fields.',
    url = 'http://www.gefasoft-muenchen.de',
    download_url = 'http://trac-hacks.org/wiki/RoadmapPlugin',
    packages=find_packages(exclude=['*.tests*']),
    entry_points = """
        [trac.plugins]
        roadmapplugin = roadmapplugin
    """,
    package_data={'roadmapplugin': ['locale/*.*',
                                    'locale/*/LC_MESSAGES/*.*']},
)

