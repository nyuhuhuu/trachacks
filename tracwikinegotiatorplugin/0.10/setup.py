from setuptools import setup

PACKAGE = 'TracWikiNegotiator'
VERSION = '1.6'

setup(name=PACKAGE, version=VERSION,
      description='Content negotiation plugin for Trac wiki page.',
      author='Shun-ichi Goto',
      author_email='shunichi.goto@gmail.com',
      keywords='trac plugin localization l10n wiki',
      license='BSD',
      long_description = """
      This plugin provides content negotiation mechanism for Trac wiki
      pages.  With this plugin, the trac site can provides localized
      pages for users.
      """,
      packages=['wikinegotiator'],
      package_data = {'wikinegotiator': ['templates/*.cs', 'htdocs/css/*.css']},
      data_files=['README'],
      entry_points={'trac.plugins': 'TracWikiNegotiator = wikinegotiator'},
      )
