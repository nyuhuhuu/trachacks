"""
 Copyright (c) 2008-2009 by Martin Scharrer <martin@scharrer-online.de>
"""

__url__      = ur"$URL$"[6:-2]
__author__   = ur"$Author$"[9:-2]
__revision__ = r"$Rev$"[6:-2]
__date__     = r"$Date$"[7:-2]


from trac.core import *
from trac.wiki.api import IWikiMacroProvider
from trac.wiki.macros import WikiMacroBase
from trac.wiki.formatter import format_to_oneliner
from genshi.builder import tag
from trac.util import format_datetime, pretty_timedelta
from trac.util.datefmt import utc, to_datetime, from_utimestamp, to_utimestamp, format_date
from urllib import quote_plus
from trac.web.api import IRequestFilter
from trac.web.chrome import add_stylesheet, ITemplateProvider
from trac.util.text import to_unicode
from time import time as unixtime
from tracadvparseargs import parse_args

class ListOfWikiPagesComponent(Component):
    implements ( IWikiMacroProvider, IRequestFilter, ITemplateProvider )

    rev = __revision__
    date = __date__

    long_format = False

    tunits = {
        's': 1,
        'm': 60,
        'h': 60*60,
        'd': 60*60*24,
        'w': 60*60*24*7,
        'o': 60*60*24*30,
        'y': 60*60*24*365
    }
    tunits_name = {
        's': ' second',
        'm': ' minute',
        'h': ' hour',
        'd': ' day',
        'w': ' week',
        'o': ' month',
        'y': ' year'
    }

   # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        add_stylesheet( req, 'listofwikipages/style.css')
        return (template, data, content_type)


   # ITemplateProvider methods
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('listofwikipages', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []

    def get_macros(self):
      return ('ListOfWikiPages','LastChangesBy')


    def timeval(self, name, default):
      if name in self.kwargs:
        try:
          val = self.kwargs[name]
          try:
            val = int(val)
            text = \
                str(val) + self.tunits_name['s'] + ['s',''][val == 1]
          except:
            unit = val[-1].lower()
            val = float(val[:-1])
            text = \
                str(val).strip('.0') + self.tunits_name[unit] \
                + ['s',''][val == 1]
            val =  int( val * self.tunits[ unit ] )
          val = int(unixtime()) - val
          # mod for trac 0.12
          nval = to_utimestamp(to_datetime(val))
          
        except:
          raise TracError("Invalid value '%s' for argument '%s'! "
              % (self.kwargs[name],name) )
        return (nval,text)
      else:
        defval, deftext = default
        ndef = to_utimestamp(to_datetime(defval))
        return (ndef,deftext)


    def formattime(self,time):
        """Return formatted time for ListOfWikiPages table."""
        # mod for 0.12 timestamp
        ntime = from_utimestamp(time)
        return [ tag.span( format_datetime  ( ntime ) ),
                 tag.span(
                    " (", 
                    tag.a( pretty_timedelta ( ntime ),
                           href = self.href('timeline',
                                  precision='seconds', from_=
                                  quote_plus( format_datetime (ntime,'iso8601') )
                           ) ),
                    " ago)"
                 )
               ]

    def formatrow(self, n, name, time, version='', comment='', author=''):
        name = to_unicode(name)
        namelink = tag.a( name, href = self.href.wiki( name ) )
        cols = [ tag.td( namelink ), tag.td( self.formattime( time )) ]
        if author:
            cols.append ( tag.td( author )  )
        if self.long_format:
            cols.extend ([
              tag.td( tag.a(version,
                href=self.href.wiki( name, version=version)), class_='version'),
              tag.td( tag.a("Diff",
                href=self.href.wiki( name, action='diff', version=version) ) ),
              tag.td( tag.a("History",
                href=self.href.wiki( name, action='history') ) ),
              tag.td( comment ),
            ])
        return tag.tr(
                  cols,
                  class_ = ('even','odd')[ n % 2 ]
               )

    def get_macro_description(self,name):
        if name == 'ListOfWikiPages':
          return self.ListOfWikiPages.__doc__
        elif name == 'LastChangesBy':
          return self.LastChangesBy.__doc__
        else:
          return ''


    def expand_macro(self, formatter, name, content):
        if name == 'ListOfWikiPages':
          return self.ListOfWikiPages(formatter, content)
        elif name == 'LastChangesBy':
          return self.LastChangesBy(formatter, content)
        else:
          return tag()

    def _get_sql_exclude(self, list):
      import re
      if not list:
        return ''
      star  = re.compile(r'(?<!\\)\*')
      ques  = re.compile(r'(?<!\\)\?')
      sql_exclude = ''
      for pattern in list:
        pattern = pattern.replace('%',r'\%').replace('_',r'\_')
        pattern = star.sub('%', pattern)
        pattern = ques.sub('_', pattern)
        sql_exclude = sql_exclude + " AND name NOT LIKE '%s' " % pattern
      #sql_exclude = sql_exclude + r" ESCAPE '\\' "
      return sql_exclude

    def ListOfWikiPages(self, formatter, content):
        """
== Description ==

Website: http://trac-hacks.org/wiki/ListOfWikiPagesMacro

`$Id$`

The macro `ListOfWikiPages` prints a table of all (user generated, i.e. 
non-trac-default) wiki pages with last changed date and author as requested in 
Request-a-Hack th:#2427.
Version 0.2 provides also a long format which also includes the newest version 
number and links to the difference and the history as well as the last comment.  
This was requested by th:#4717.

The second macro provided by this package is `LastChangesBy` which prints the 
last changes made by the given user or the logged-in user if no username is 
given. 

== Usage ==

You can use the `ListOfWikiPages` macro like this:
{{{
[[ListOfWikiPages]]                     # default format as configured in the config file
[[ListOfWikiPages(format=short)]]       # short format
[[ListOfWikiPages(format=long)]]        # long format (new v0.2)
}}}
which prints a table of all wiki pages, or with a list of wiki pages:
{{{
[[ListOfWikiPages(ThatWikiPage,ThisWikiPage,AnotherWikiPage,format=...)]]
}}}

Since v0.3 the optional arguments `from` and `to` can be used to specify a 
time/date range as requested by th:#5344.
The values of this arguments are taken as negative offsets to the current time 
(i.e. the time the wiki page is displayed).
Allowed is a number followed by a unit which can be `s`,`m`,`h`,`d`,`w`,`o`,`y` 
for seconds, minutes, hours, days, weeks, month and years.
If the unit is missing seconds are assumed.

{{{
[[ListOfWikiPages(from=3d)]]            # displays all wiki pages changed in the last three days
[[ListOfWikiPages(to=15m)]]             # displays all wiki pages was where changed longer than 15 minutes ago
[[ListOfWikiPages(from=4.5w,to=15h)]]   # displays all wiki pages was where changed between 4 1/2 week and 15 hours ago
}}}

A headline can be given using a `headline` argument:
{{{
[[ListOfWikiPages(headline=Headline text without any comma)]]     # sets a table headline, may not contain '`,`'
}}}

The order can be reversed, i.e. list the oldest wikis first, using:
{{{
[[ListOfWikiPages(order=reverse)]]
}}}

Unwanted wiki ranges (e.g. `Trac*`) can be excluded by the `exclude=pattern` option which can be given multiple times.
The wildcards '`*`' (matches everything) and '`?`' (matches a single character) can be used in the pattern. (Requested by #6074)
{{{
[[ListOfWikiPages(exclude=Trac*,exclude=abc?)]]
}}}

        """
        largs, kwargs = parse_args( content, multi = ['exclude'] )

        self.href = formatter.req.href
        section = 'listofwikipages'

        long_format = self.env.config.get(section, 'default_format', 
            'short').lower() == 'long'
        if 'format' in kwargs:
          long_format = kwargs['format'].lower() == 'long'
        self.long_format = long_format

        ignoreusers = self.env.config.getlist(section, 'ignore_users', ['trac'])

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        if largs:
            sql_wikis = " AND name IN ('"    \
                        + "','".join(largs) \
                        + "') "
        else:
            sql_wikis = ''

        sql_exclude = ''
        if 'exclude' in kwargs:
          sql_exclude = self._get_sql_exclude(kwargs['exclude'])

        self.kwargs = kwargs
        dfrom, fromtext = self.timeval('from', (0,''))
        dto, totext     = self.timeval('to',   (int(unixtime()),''))
       
       
        if 'from' in kwargs or 'to' in kwargs:
          sql_time = " time BETWEEN %d AND %d AND " % (dfrom,dto)
        else:
          sql_time = ''

        if kwargs.get('order','normal') == 'reverse':
          order = " "
        else:
          order = " DESC "

        cursor.execute(
            "SELECT name,time,author,version,comment FROM wiki AS w1 WHERE " \
            + sql_time + \
            "author NOT IN ('%s') "  % "','".join( ignoreusers ) + sql_wikis + sql_exclude + \
            "AND version=(SELECT MAX(version) FROM wiki AS w2 WHERE w1.name=w2.name) ORDER BY time " + \
            order)
        rows = [ self.formatrow(n,name,time,version,comment,author)
              for n,[name,time,author,version,comment] in enumerate(cursor) ]

        if self.long_format:
          cols = ( "WikiPage", "Last Changed At", "By",
                   "Version", "Diff", "History", "Comment" )
        else:
          cols = ( "WikiPage", "Last Changed At", "By" )

        if 'headline' in kwargs:
          headlinetag = tag.tr( tag.th( kwargs['headline'],
            colspan = len(cols) ) )
        else:
          headlinetag = tag()

        head  = tag.thead ( headlinetag, tag.tr(
          map(lambda x: tag.th(x, class_=x.replace(" ", "").lower() ), cols) ) )
        table = tag.table ( head, rows, class_ = 'listofwikipages' )

        self.href = None
        return table


    def LastChangesBy(self, formatter, content):
        """
This macro prints a table similar to the `[[ListOfWikiPages]]` only with the 
''By'' column missing and the author name in the table head.
{{{
[[LastChangesBy(martin_s)]]          # the last 5 changes by user `martin_s`
[[LastChangesBy(martin_s,10)]]       # the last 10 changes by user `martin_s`

[[LastChangesBy]]                    # or
[[LastChangesBy()]]                  # the last 5 changes by the current user (i.e. every user sees it's own changes, if logged-on)
[[LastChangesBy(,12)]]               # the last 12 changes by the current user

[[LastChangesBy(...,format=...]]     # Selects `long` or `short` table format
[[LastChangesBy(...,from=..,to=..]]  # Selects `from` and `to` time/date range

[[LastChangesBy(...,headline=...]]   # Overwrites headline, may not contain `','`

[[LastChangesBy(...,order=reverse]]  # Lists the wikis in reverse order. Only really useful with few wikis or with `to`/`from`.

[[LastChangesBy(..,exclude=pattern]] # Excludes wikis matching `pattern`. Wildcards `*` and `?` are supported.
}}}
        """

        largs, kwargs = parse_args( content )

        #self.base_path = formatter.req.base_path
        self.href = formatter.req.href
        section = 'listofwikipages'

        long_format = self.env.config.get(section, 'default_format', 
            'short').lower() == 'long'
        if 'format' in kwargs:
          long_format = kwargs['format'].lower() == 'long'
        self.long_format = long_format

        self.kwargs = kwargs
        dfrom, fromtext = self.timeval('from', (0,''))
        dto, totext     = self.timeval('to',   (int(unixtime()),''))

        if 'from' in kwargs or 'to' in kwargs:
          sql_time = " AND time BETWEEN %d AND %d " % (dfrom,dto)
        else:
          sql_time = ''

        sql_exclude = ''
        if 'exclude' in kwargs:
          sql_exclude = self._get_sql_exclude(kwargs['exclude'])

        author = len(largs) > 0 and largs[0] or formatter.req.authname
        count  = len(largs) > 1 and largs[1] or 5
        try:
            count = int(count)
            if count < 1:
                raise
        except:
            raise TracError("Second list argument must be a positive integer!")

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        if kwargs.get('order','normal') == 'reverse':
          order = " "
        else:
          order = " DESC "

        cursor.execute ( """
              SELECT name,time,version,comment
              FROM wiki AS w1 WHERE author = %s """ + sql_time + sql_exclude + """
              AND version=(SELECT MAX(version) FROM wiki AS w2 WHERE w1.name=w2.name)
              ORDER BY time
          """ + order + " LIMIT 0,%s ", (author, str(count)) )

        rows = [ self.formatrow(n,name,time,version,comment) for
              n,[name,time,version,comment] in enumerate(cursor) if n < count ]
        if count == 1:
            count = ''
            s = ''
        else:
            s = 's'

        if self.long_format:
          cols = ( "WikiPage", "Last Changed At",
                   "Version", "Diff", "History", "Comment" )
        else:
          cols = ( "WikiPage", "Last Changed At" )

        headline = "Last %s change%s by  " % (count,s)
        if sql_time:
          if fromtext:
            if totext:
              timetag = " between %s and %s ago" % (fromtext,totext)
            else:
              timetag = " in the last %s" % fromtext
          else:
            if totext:
              timetag = " before the last %s" % totext
            else:
              timetag = ""
        else:
          timetag = ''

        if 'headline' in kwargs:
          headlinetag = tag.tr(
              tag.th(kwargs['headline'],
              colspan = len(cols) ))
        else:
          headlinetag = tag.tr(
              tag.th(headline, tag.strong(author), timetag,
              colspan = len(cols) ))

        head = tag.thead ( headlinetag,
                tag.tr(
          map(lambda x: tag.th(x, class_=x.replace(" ", "").lower() ), cols)
        ) )
        table = tag.table( head, rows, class_ = 'lastchangesby' )

        self.href = None
        return table

