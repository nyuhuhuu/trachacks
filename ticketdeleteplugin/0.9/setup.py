#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

from setuptools import setup

setup(
    name = 'TracTicketDelete',
    version = '0.1',
    packages = ['ticketdelete'],
    package_data = { 'ticketdelete': ['templates/*.cs' ] },

    author = "Noah Kantrowitz",
    author_email = "noah@coderanger.net",
    description = "A small plugin to remove tickets and ticket changes from Trac.",
    long_description = "Provides a web interface to removing whole tickets, and ticket changes.",
    license = "BSD",
    keywords = "trac plugin ticket delete",
    url = "http://trac-hacks.org/wiki/TicketDeletePlugin",
    
    #install_requires = ['TracWebAdmin'],

    entry_points = {
        'trac.plugins': [
            'ticketdelete.web_ui = ticketdelete.web_ui'
        ]
    }
)
