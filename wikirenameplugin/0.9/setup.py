#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from setuptools import setup

setup(
    name = 'TracWikiRename',
    version = '0.1-r1',
    packages = ['wikirename'],
    package_data={ 'wikirename' : [ 'templates/*.cs' ] },

    author = "Noah Kantrowitz",
    author_email = "noah@coderanger.net",
    description = "Add simple support for renaming/moving wiki pages",
    long_description = """Adds basic support for renaming wiki pages. A console script is provided, as is a WebAdmin module. \
                          Please read the notice on the homepage for a list of known shortcomings.""",
    license = "BSD",
    keywords = "trac plugin wiki page rename",
    url = "http://trac-hacks.org/wiki/WikiRenamePlugin",

    entry_points = {
        'trac.plugins': [
            'wikirename.web_ui = wikirename.web_ui',
        ],
        'console_scripts': [
            'trac-wikirename = wikirename.script:run'
        ],
    },
    
    #install_requires = [ 'TracWebAdmin', 'TracCtxtnavAdd' ],
)
