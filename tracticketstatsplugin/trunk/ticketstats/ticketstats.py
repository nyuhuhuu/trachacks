# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Prentice Wongvibulsin <me@prenticew.com>
# Copyright (c) 2010-2013 Ryan J Ollos <ryan.j.ollos@gmail.com>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import re

from genshi.builder import tag

from trac.core import *
from trac.config import Option, IntOption
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.ticket import Milestone

from datetime import date, datetime, time, timedelta
from trac.util.datefmt import format_date, parse_date, to_utimestamp, utc

# ************************
DEFAULT_DAYS_BACK = 30 * 6
DEFAULT_INTERVAL = 30
# ************************


class TicketStatsPlugin(Component):
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    yui_base_url = Option('ticketstats', 'yui_base_url',
                          default='http://yui.yahooapis.com/2.9.0',
                          doc='Location of YUI API')

    default_days_back = IntOption('ticketstats', 'default_days_back',
                                  default=DEFAULT_DAYS_BACK,
                                  doc='Number of days to show by default')

    default_interval = IntOption('ticketstats', 'default_interval',
                                 default=DEFAULT_INTERVAL,
                                 doc='Number of days between each data point'
                                     ' (resolution) by default')

    ### INavigationContributor methods

    def get_active_navigation_item(self, req):
        return 'ticketstats'

    def get_navigation_items(self, req):
        if req.perm.has_permission('REPORT_VIEW'):
            yield ('mainnav', 'ticketstats',
                   tag.a('Ticket Stats', href=req.href.ticketstats()))

    ### Internal methods

    def _get_num_closed_tix(self, from_date, at_date, milestone):
        """Returns an integer of the number of close ticket events counted
        between from_date to at_date."""

        status_map = {'new': 0,
                      'reopened': 0,
                      'assigned': 0,
                      'closed': 1,
                      'edit': 0}

        count = 0

        ma_milestone_str = ""
        if milestone is not None:
            ma_milestone_str = " AND t.milestone = \"%s\" " % milestone

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        # TODO clean up this query
        cursor.execute("""
            SELECT t.id, tc.field, tc.time, tc.oldvalue, tc.newvalue,
              t.priority
            FROM enum p, ticket_change tc
              INNER JOIN ticket t ON t.id = tc.ticket AND tc.time > %s
                AND tc.time <= %s
            WHERE p.name = t.priority AND p.type = 'priority' %s
            ORDER BY tc.time""" % (to_utimestamp(from_date),
                                   to_utimestamp(at_date), ma_milestone_str))

        for tid, field, time, old, status, priority in cursor:
            if field == 'status':
                if status in ('new', 'assigned', 'reopened', 'closed', 'edit'):
                    count += status_map[status]

        return count

    def _get_num_open_tix(self, at_date, milestone):
        """Returns an integer of the number of tickets currently open on that
        date."""

        status_map = {'new': 0,
                      'reopened': 1,
                      'assigned': 0,
                      'closed': -1,
                      'edit': 0}

        count = 0

        ma_milestone_str = ""
        if milestone is not None:
            ma_milestone_str = " AND t.milestone = \"%s\" " % milestone

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        # TODO clean up this query
        cursor.execute("""
            SELECT t.type AS type, owner, status, time
            FROM ticket t, enum p
            WHERE p.name = t.priority AND p.type = 'priority'
              AND t.time <= %s %s
            """ % (to_utimestamp(at_date), ma_milestone_str))

        for rows in cursor:
            count += 1

        # TODO clean up this query
        cursor.execute("""
            SELECT t.id, tc.field, tc.time, tc.oldvalue, tc.newvalue,
              t.priority
            FROM enum p, ticket_change tc
              INNER JOIN ticket t ON t.id = tc.ticket AND tc.time > 0
                AND tc.time <= %s WHERE p.name = t.priority
                AND p.type = 'priority' %s
            ORDER BY tc.time""" % (to_utimestamp(at_date), ma_milestone_str))

        for tid, field, time, old, status, priority in cursor:
            if field == 'status':
                if status in ('new', 'assigned', 'reopened', 'closed', 'edit'):
                    count += status_map[status]

        return count

    ### IRequestHandler methods

    def match_request(self, req):
        return re.match(r'/ticketstats(?:_trac)?(?:/.*)?$', req.path_info)

    def process_request(self, req):
        req.perm.require('REPORT_VIEW')
        req_content = req.args.get('content')
        milestone = None

        if not None in [req.args.get('end_date'), req.args.get('start_date'),
                        req.args.get('resolution')]:
            # form submit
            grab_at_date = req.args.get('end_date')
            grab_from_date = req.args.get('start_date')
            grab_resolution = req.args.get('resolution')
            grab_milestone = req.args.get('milestone')
            if grab_milestone == "__all":
                milestone = None
            else:
                milestone = grab_milestone

            # validate inputs
            if None in [grab_at_date, grab_from_date]:
                raise TracError('Please specify a valid range.')

            if None in [grab_resolution]:
                raise TracError('Please specify the graph interval.')

            if 0 in [len(grab_at_date), len(grab_from_date),
                     len(grab_resolution)]:
                raise TracError(
                    'Please ensure that all fields have been filled in.')

            if not grab_resolution.isdigit():
                raise TracError(
                    'The graph interval field must be an integer, days.')

            at_date = parse_date(grab_at_date)
            at_date = datetime.combine(at_date,
                                       time(11, 59, 59, 0, utc))  # Add tzinfo

            from_date = parse_date(grab_from_date)
            from_date = datetime.combine(from_date,
                                         time(0, 0, 0, 0, utc))  # Add tzinfo

            graph_res = int(grab_resolution)

        else:
            # default data
            todays_date = date.today()
            at_date = datetime.combine(todays_date, time(11, 59, 59, 0, utc))
            from_date = at_date - timedelta(self.default_days_back)
            graph_res = self.default_interval

        count = []

        # Calculate 0th point
        last_date = from_date - timedelta(graph_res)
        last_num_open = self._get_num_open_tix(last_date, milestone)

        # Calculate remaining points
        for cur_date in date_range(from_date, at_date, graph_res):
            num_open = self._get_num_open_tix(cur_date, milestone)
            num_closed = self._get_num_closed_tix(last_date, cur_date,
                                                  milestone)
            date_str = format_date(cur_date)
            if graph_res != 1:
                date_str = "%s thru %s" % (format_date(last_date), date_str)
            count.append({'date': date_str,
                          'new': num_open - last_num_open + num_closed,
                          'closed': num_closed,
                          'open': num_open})
            last_num_open = num_open
            last_date = cur_date

        # if chart data is requested, raw text is returned rather than data
        # object for templating
        if req_content is not None and req_content == "chartdata":
            js_data = '{"chartdata": [\n'
            for x in count:
                js_data += '{"date": "%s",' % x['date']
                js_data += ' "new_tickets": %s,' % x['new']
                js_data += ' "closed": %s,' % x['closed']
                js_data += ' "open": %s},\n' % x['open']
            js_data = js_data[:-2] + '\n]}'
            req.send(js_data.encode('utf-8'))
            return
        else:
            db = self.env.get_db_cnx()
            show_all = req.args.get('show') == 'all'
            milestone_list = [m.name for m in
                              Milestone.select(self.env, show_all, db)]
            if milestone is None:
                milestone_num = 0
            elif milestone in milestone_list:
                milestone_num = milestone_list.find(milestone)
            else:
                milestone_num = 0

            data = {
                'ticket_data': count,
                'start_date': format_date(from_date),
                'end_date': format_date(at_date),
                'resolution': str(graph_res),
                'baseurl': req.base_url,
                'milestones': milestone_list,
                'cmilestone': milestone_num,
                'yui_base_url': self.yui_base_url
            }

            return 'greensauce.html', data, None

    ### ITemplateProvider methods

    def get_htdocs_dirs(self):
        return []

    def get_templates_dirs(self):
        from pkg_resources import resource_filename

        return [resource_filename(__name__, 'templates')]


def date_range(begin, end, delta=timedelta(1)):
    """Stolen from:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/574441

    Form a range of dates and iterate over them.  

    Arguments:
    begin -- a date (or datetime) object; the beginning of the range.
    end   -- a date (or datetime) object; the end of the range.
    delta -- (optional) a timedelta object; how much to step each iteration.
             Default step is 1 day.
             
    Usage:

    """
    if not isinstance(delta, timedelta):
        delta = timedelta(delta)

    ZERO = timedelta(0)

    if begin < end:
        if delta <= ZERO:
            raise StopIteration
        test = end.__gt__
    else:
        if delta >= ZERO:
            raise StopIteration
        test = end.__lt__

    while test(begin):
        yield begin
        begin += delta
