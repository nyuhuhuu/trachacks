# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Ryan J Ollos <ryan.j.ollos@gmail.com>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

from unittest import TestSuite


def test_suite():
    suite = TestSuite()
    
    import trachours.tests.hours
    suite.addTest(trachours.tests.hours.test_suite())
    import trachours.tests.ticket
    suite.addTest(trachours.tests.ticket.test_suite())
    
    return suite


def revert_trachours_schema_init(db):
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS ticket_time")
    cursor.execute("DROP TABLE IF EXISTS ticket_time_query")
    cursor.execute("DELETE FROM system WHERE name='trachours.db_version'")
