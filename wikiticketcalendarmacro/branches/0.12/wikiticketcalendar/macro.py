# -*- coding: utf-8 -*-
# Copyright (C) 2005 Matthew Good <trac@matt-good.net>
# Copyright (C) 2005 Jan Finell <finell@cenix-bioscience.com>
# Copyright (C) 2007 Mike Comb <mcomb@mac.com>
# Copyright (C) 2008 JaeWook Choi <http://trac-hacks.org/wiki/butterflow>
# Copyright (C) 2008, 2009 W. Martin Borgert <debacle@debian.org>
# Copyright (C) 2010 Steffen Hoffmann <hoff.st@shaas.net>
#
# "THE BEER-WARE LICENSE" (Revision 42):
# <trac@matt-good.net> wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff.  If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return.  Matthew Good
# (Beer-ware license written by Poul-Henning Kamp
#  http://people.freebsd.org/~phk/)
#
# Author: Matthew Good <trac@matt-good.net>
# See changelog for a detailed history


import calendar
import sys
import time

from datetime               import datetime
from inspect                import getdoc
from pkg_resources          import resource_filename
from string                 import replace

from genshi.core            import Markup

from trac.config            import Option
from trac.core              import implements
from trac.util.datefmt      import to_utimestamp, FixedOffset
from trac.util.text         import to_unicode
from trac.util.translation  import domain_functions
from trac.web.href          import Href
from trac.web.chrome        import add_stylesheet, ITemplateProvider
from trac.wiki.api          import IWikiMacroProvider, WikiSystem
from trac.wiki.macros       import WikiMacroBase

_, tag_, N_, add_domain = \
    domain_functions('wikiticketcalendar', '_', 'tag_', 'N_', 'add_domain')


__all__ = ['WikiTicketCalendarMacro', ]


class WikiTicketCalendarMacro(WikiMacroBase):
    """Display Milestones and Tickets in a calendar view.

    displays a calendar, the days link to:
     - milestones (day in bold) if there is one on that day
     - a wiki page that has wiki_page_format (if exist)
     - create that wiki page if it does not exist
     - use page template (if exist) for new wiki page

    Activate it in 'trac.ini':
    --------
    [components]
    wikiticketcalendar.* = enabled

    Usage
    -----
    WikiTicketCalendar([year,month,[showbuttons,[wiki_page_format,
        [show_ticket_open_dates,[wiki_page_template]]]]])

    Arguments
    ---------
    year, month = display calendar for month in year
                  ('*' for current year/month)
    showbuttons = true/false, show prev/next buttons
    wiki_page_format = strftime format for wiki pages to display as link
                       (if there is not a milestone placed on that day)
                       (if exist, otherwise link to create page)
                       default is "%Y-%m-%d", '*' for default
    show_ticket_open_dates = true/false, show also when a ticket was opened
    wiki_page_template = wiki template tried to create new page

    Examples
    --------
    WikiTicketCalendar(2006,07)
    WikiTicketCalendar(2006,07,false)
    WikiTicketCalendar(*,*,true,Meeting-%Y-%m-%d)
    WikiTicketCalendar(2006,07,false,Meeting-%Y-%m-%d)
    WikiTicketCalendar(2006,07,true,*,true)
    WikiTicketCalendar(2006,07,true,Meeting-%Y-%m-%d,true,Meeting)
    """

    implements(IWikiMacroProvider, ITemplateProvider)

    def __init__(self):
        # bind the 'foo' catalog to the specified locale directory
        locale_dir = resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)

        # Read options from trac.ini's [datafield] section, if existing
        self.date_format = Option('datefield', 'format', default='ymd',
            doc="""
            The format to use for dates. Valid values are dmy, mdy, and ymd.
            """)
        self.date_sep = Option('datefield', 'separator', default='-',
            doc="The separator character to use for dates.")

    # ITemplateProvider methods
    # Returns additional path where stylesheets are placed.
    def get_htdocs_dirs(self):
        return [('wikiticketcalendar', resource_filename(__name__, 'htdocs'))]

    # Returns additional path where templates are placed.
    def get_templates_dirs(self):
        return []

    # IWikiMacroProvider methods
    # Returns list of provided macro names.
    def get_macros(self):
        yield "WikiTicketCalendar"

    # Returns documentation for provided macros.
    def get_macro_description(self, name):
        return getdoc(self.__class__)

    # Returns macro content.
    def expand_macro(self, formatter, name, arguments):

        today = time.localtime()
        http_param_year = formatter.req.args.get('year','')
        http_param_month = formatter.req.args.get('month','')
        if arguments == "":
            args = []
        else:
            args = arguments.split(',')

        # find out whether use http param, current or macro param year/month

        if http_param_year == "":
            # not clicked on a prev or next button
            if len(args) >= 1 and args[0] <> "*":
                # year given in macro parameters
                year = int(args[0])
            else:
                # use current year
                year = today.tm_year
        else:
            # year in http params (clicked by user) overrides everything
            year = int(http_param_year)

        if http_param_month == "":
            # not clicked on a prev or next button
            if len(args) >= 2 and args[1] <> "*":
                # month given in macro parameters
                month = int(args[1])
            else:
                # use current month
                month = today.tm_mon
        else:
            # month in http params (clicked by user) overrides everything
            month = int(http_param_month)

        showbuttons = True
        if len(args) >= 3:
            showbuttons = args[2] in ["True", "true", "yes", "1"]

        wiki_page_format = "%Y-%m-%d"
        if len(args) >= 4 and args[3] != "*":
            wiki_page_format = args[3]

        show_ticket_open_dates = True
        if len(args) >= 5:
            show_ticket_open_dates = args[4] in ["True", "true", "yes", "1"]

        # template name tried to create new pages
        # optional, default (empty page) is used, if name is invalid
        wiki_page_template = ""
        if len(args) >= 6:
            wiki_page_template = args[5]

        curr_day = None
        if year == today.tm_year and month == today.tm_mon:
            curr_day = today.tm_mday

        # Can use this to change the day the week starts on,
        # but this is a system-wide setting.
        calendar.setfirstweekday(calendar.MONDAY)
        cal = calendar.monthcalendar(year, month)

        date = [year, month + 1] + [1] * 7

        # URL to the current page (used in the navigation links)
        thispageURL = Href(formatter.req.base_path + formatter.req.path_info)
        # for the prev/next navigation links
        prevMonth = month - 1
        nextMonth = month + 1
        nextYear = prevYear = year
        # check for year change (KISS version)
        if prevMonth == 0:
            prevMonth = 12
            prevYear -= 1
        if nextMonth == 13:
            nextMonth = 1
            nextYear += 1
        # prepare a fast-forward/-rewind
        ffYear = frYear = year
        if month < 3:
            frMonth = month + 9
            frYear -= 1
        else:
            frMonth = month - 3
        if month > 9:
            ffMonth = month - 9
            frYear += 1
        else:
            ffMonth = month + 3

        # add CSS stylesheet
        add_stylesheet(formatter.req,
            'wikiticketcalendar/css/wikiticketcalendar.css')

        # building the output
        buff = []
        buff.append('<table class="wikiTicketCalendar"><caption>')

        if showbuttons:
            # prev year link
            date[0:2] = [year-1, month]
            buff.append("""<a class="prev" href="%(url)s"
                title="%(title)s">&nbsp;&lt;&lt;</a>
                """ % {
                'url': thispageURL(month=month, year=year-1),
                'title': _("Turn up %s") %
                    to_unicode(time.strftime('%B %Y', tuple(date)))
                })
            # fast-rewind month link
            date[0:2] = [frYear, frMonth]
            buff.append("""<a class="prev" href="%(url)s"
                title="%(title)s">&nbsp;&lt;&nbsp;</a>
                """ % {
                'url': thispageURL(month=frMonth, year=frYear),
                'title': _("Turn up %s") %
                    to_unicode(time.strftime('%B %Y', tuple(date)))
                })
            # prev month link
            date[0:2] = [prevYear, prevMonth]
            buff.append("""<a class="prev" href="%(url)s"
                title="%(title)s">&nbsp;&laquo;&nbsp;</a>
                """ % {
                'url': thispageURL(month=prevMonth, year=prevYear),
                'title': _("Turn up %s") %
                    to_unicode(time.strftime('%B %Y', tuple(date)))
                })

        # the caption
        date[0:2] = [year, month]
        buff.append(to_unicode(time.strftime('<strong>%B %Y</strong>',
                                                      tuple(date))))

        if showbuttons:
            # next month link
            date[0:2] = [nextYear, nextMonth]
            buff.append("""<a class="next" href="%(url)s"
                title="%(title)s">&nbsp;&raquo;&nbsp;</a>
                """ % {
                'url': thispageURL(month=nextMonth, year=nextYear),
                'title': _("Turn up %s") %
                    to_unicode(time.strftime('%B %Y', tuple(date)))
                })
            # fast-forward month link
            date[0:2] = [ffYear, ffMonth]
            buff.append("""<a class="next" href="%(url)s"
                title="%(title)s">&nbsp;&gt;&nbsp;</a>
                """ % {
                'url': thispageURL(month=ffMonth, year=ffYear),
                'title': _("Turn up %s") %
                    to_unicode(time.strftime('%B %Y', tuple(date)))
                })
            # next year link
            date[0:2] = [year+1, month]
            buff.append("""<a class="next" href="%(url)s"
                title="%(title)s">&nbsp;&gt;&gt;</a>
                """ % {
                'url': thispageURL(month=month, year=year+1),
                'title': _("Turn up %s") %
                    to_unicode(time.strftime('%B %Y', tuple(date)))
                })

        buff.append('</caption>\n<thead><tr align="center">')
        date[0:2] = [year, month]

        for day in calendar.weekheader(2).split()[:-2]:
            buff.append("""<th class="workday"
                        scope="col"><b>%s</b></th>
                        """ % day)
        for day in calendar.weekheader(2).split()[-2:]:
            buff.append("""<th class="weekend"
                        scope="col"><b>%s</b></th>
                        """ % day)
        buff.append('</tr></thead>\n<tbody>\n')

        for row in cal:
            buff.append('<tr align="right">')
            for day in row:
                if not day:
                    buff.append('<td class="day">')
                else:
                    # first check for milestone on that day
                    db = self.env.get_db_cnx()
                    cursor = db.cursor()
                    utc = FixedOffset(0, 'UTC')
                    duedatestamp = t = to_utimestamp(datetime(year, month,
                                           day, 0, 0, 0, 0, tzinfo=utc))
                    duedatestamp_eod = t + 86399999999

                    dayString = "%02d" % day
                    monthString = "%02d" % month
                    yearString = "%04d" % year

                    # check for wikipage with name specified in
                    # 'wiki_page_format'
                    date[0:3] = [year, month, day]
                    wiki = time.strftime(wiki_page_format, tuple(date))
                    url = self.env.href.wiki(wiki)
                    if WikiSystem(self.env).has_page(wiki):
                        a_classes = "day_haspage"
                        title = _("Go to page %s") % wiki
                    else:
                        a_classes = "day"
                        url += "?action=edit"
                        # adding template name, if specified
                        if wiki_page_template != "":
                            url += "&template=" + wiki_page_template
                        title = _("Create page %s") % wiki

                    buff.append("""<td class="%(td_classes)s"
                        valign="top"><a class="%(a_classes)s" href="%(url)s"
                        title="%(title)s"><b>%(day)s</b></a>
                        """ % {
                        'day': day,
                        'title': title,
                        'url': url,
                        'td_classes': day == curr_day and 'today' or 'day',
                        'a_classes': a_classes,
                    })

                    # Use get to handle default format
                    duedate = { 'dmy': '%(dd)s%(sep)s%(mm)s%(sep)s%(yy)s',
                                'mdy': '%(mm)s%(sep)s%(dd)s%(sep)s%(yy)s',
                                'ymd': '%(yy)s%(sep)s%(mm)s%(sep)s%(dd)s'
                    }.get(self.date_format,
                    '%(yy)s%(sep)s%(mm)s%(sep)s%(dd)s') % {
                        'dd': dayString,
                        'mm': monthString,
                        'yy': yearString,
                        'sep': self.date_sep
                    }

                    cursor.execute("""
                        SELECT name
                          FROM milestone
                         WHERE due=%s
                    """, (duedatestamp,))
                    while (1):
                        row = cursor.fetchone()
                        if row == None:
                            buff.append('<br>')
                            break
                        else:
                            name = row[0]
                            url = self.env.href.milestone(name)
                            buff.append("""<div class="milestone"><a
                                href="%(url)s">* %(name)s</a></div>
                                """ % {
                                'name': name,
                                'url': url,
                            })

                    cursor.execute("""
                        SELECT t.id,t.summary,t.keywords,
                               t.owner,t.status,t.description
                          FROM ticket t, ticket_custom tc
                         WHERE tc.ticket=t.id and tc.name='due_close' and
                               tc.value=%s
                    """, (duedate, ))
                    while (1):
                        row = cursor.fetchone()
                        if row == None:
                            break
                        else:
                            id = row[0]
                            url = self.env.href.ticket(id)
                            ticket = row[1]
                            keyword = row[2]
                            owner = row[3]
                            status = row[4]
                            description = row[5][:1024]
                            buff.append("""<div class="%(classes)s"
                                align="left"><a href="%(url)s"
                                title=\'%(description)s\'
                                target="_blank">#%(id)s</a> %(ticket)s
                                (%(owner)s)</div>
                                """ % {
                                'id': id,
                                'url': url,
                                'day': day,
                                'ticket': ticket[0:100],
                                'owner': owner,
                                'classes': status == 'closed' and
                                    'closed' or 'open',
                                'description': replace(description,
                                    "\'", "&#39;"),
                            })

                    if show_ticket_open_dates:
                        cursor.execute("""
                            SELECT t.id,t.summary,t.keywords,
                                   t.owner,t.status,t.description,t.time
                              FROM ticket t
                        """)
                        while (1):
                            row = cursor.fetchone()
                            if row == None:
                                break
                            else:
                                id = row[0]
                                url = self.env.href.ticket(id)
                                ticket = row[1]
                                keyword = row[2]
                                owner = row[3]
                                status = row[4]
                                description = row[5][:1024]
                                ticket_time = int(row[6])
                                if ticket_time < duedatestamp or \
                                        ticket_time > duedatestamp_eod:
                                    continue
                                buff.append("""
                                    <div class="opendate_%(classes)s"
                                    align="left"><a href="%(url)s"
                                    title=\'%(description)s\'
                                    target="_blank">#%(id)s</a>
                                    %(ticket)s (%(owner)s)</div>
                                    """ % {
                                    'id': id,
                                    'url': url,
                                    'day': day,
                                    'ticket': ticket[0:100],
                                    'owner': owner,
                                    'classes': status == 'closed' and
                                        'closed' or 'open',
                                    'description': replace(description,
                                        "\'", "&#39;"),
                                })

                buff.append('</td>')
            buff.append('</tr>\n')

        buff.append('</tbody>\n</table>')

        table = "\n".join(buff)
        return Markup(table)
