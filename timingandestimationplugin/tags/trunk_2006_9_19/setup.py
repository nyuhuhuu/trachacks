#!/usr/bin/env python

from setuptools import setup

PACKAGE = 'timingandestimationplugin'

setup(name=PACKAGE,
      description='Plugin to make Trac support time estimation and tracking',
      keywords='trac plugin estimation timetracking',
      version='0.1.5',
      url='',
      license='http://www.opensource.org/licenses/mit-license.php',
      author='Russ Tyndall at Acceleration.net',
      author_email='russ@acceleration.net',
      long_description="""
      This Trac 0.10 plugin provides support for Time estimation and tracking.

      See http://trac-hacks.org/wiki/TimeEstimationAndQuotingSpecification for details.
      """,
      packages=[PACKAGE],
      package_data={PACKAGE : ['templates/*.cs', 'htdocs/*']},
      entry_points={'trac.plugins': '%s = %s' % (PACKAGE, PACKAGE)})
