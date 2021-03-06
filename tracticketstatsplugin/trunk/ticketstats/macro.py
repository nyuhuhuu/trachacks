# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 Guillermo M Narvaja <guillermo.narvaja@fierro-soft.com.ar>
# Copyright (c) 2013 Ryan J Ollos <ryan.j.ollos@gmail.com>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import re
import random
from datetime import timedelta, datetime

from trac.ticket.query import Query
from trac.web.chrome import Chrome
from trac.wiki.macros import WikiMacroBase
from trac.util.datefmt import utc, format_date

try:
    from trac.util.datefmt import to_utimestamp as to_timestamp
except ImportError:
    from trac.util.datefmt import to_timestamp

from ticketstats import date_range
from tracadvparseargs import parseargs           # Trac plugin

# BEGIN - Stolen from trac/util/datefmt.py@8546 on trunk
_REL_TIME_RE = re.compile(
    r'(\d+\.?\d*)\s*'
    r'(second|minute|hour|day|week|month|year|[hdwmy])s?\s*'
    r'(?:ago)?$')
_time_intervals = dict(
    second=lambda v: timedelta(seconds=v),
    minute=lambda v: timedelta(minutes=v),
    hour=lambda v: timedelta(hours=v),
    day=lambda v: timedelta(days=v),
    week=lambda v: timedelta(weeks=v),
    month=lambda v: timedelta(days=30 * v),
    year=lambda v: timedelta(days=365 * v),
    h=lambda v: timedelta(hours=v),
    d=lambda v: timedelta(days=v),
    w=lambda v: timedelta(weeks=v),
    m=lambda v: timedelta(days=30 * v),
    y=lambda v: timedelta(days=365 * v),
)
_TIME_START_RE = re.compile(r'(this|last)\s*'
                            r'(second|minute|hour|day|week|month|year)$')
_ISO_DATE_RE = re.compile(r'\d{4}-(0[1-9]|1[0-2])-([012][0-9]|3[01])')
_time_starts = dict(
    second=lambda now: now.replace(microsecond=0),
    minute=lambda now: now.replace(microsecond=0, second=0),
    hour=lambda now: now.replace(microsecond=0, second=0, minute=0),
    day=lambda now: now.replace(microsecond=0, second=0, minute=0, hour=0),
    week=lambda now: now.replace(microsecond=0, second=0, minute=0, hour=0) -
                     timedelta(days=now.weekday()),
    month=lambda now: now.replace(microsecond=0, second=0, minute=0, hour=0,
                                  day=1),
    year=lambda now: now.replace(microsecond=0, second=0, minute=0, hour=0,
                                 day=1, month=1),
)


def _parse_relative_time(text, tzinfo):
    now = datetime.now(tzinfo)
    if text == 'now':
        return now
    if text == 'today':
        return now.replace(microsecond=0, second=0, minute=0, hour=0)
    if text == 'yesterday':
        return now.replace(microsecond=0, second=0, minute=0, hour=0) - \
            timedelta(days=1)
    match = _REL_TIME_RE.match(text)
    if match:
        (value, interval) = match.groups()
        return now - _time_intervals[interval](float(value))
    match = _TIME_START_RE.match(text)
    if match:
        (which, start) = match.groups()
        dt = _time_starts[start](now)
        if which == 'last':
            if start == 'month':
                if dt.month > 1:
                    dt = dt.replace(month=dt.month - 1)
                else:
                    dt = dt.replace(year=dt.year - 1, month=12)
            else:
                dt -= _time_intervals[start](1)
        return dt
    match = _ISO_DATE_RE.match(text)
    if match:
        return datetime(int(text[:4]), int(text[5:7]), int(text[8:10]),
                        tzinfo=tzinfo)
    return None
# END - Stolen from trac/util/datefmt.py@8546 on trunk


def _parse_args(args, args_dict=None):
    # The plugin of the args parser in not good enough because it doesn't strip
    # white spaces. Since I didn't want to change the plugin itself, I'll do
    # it here.

    args_list, args_keys = parseargs.parse_args(args, strict=False)

    if args_dict is None:
        stripped_args = {}
    else:
        stripped_args = args_dict  # This way we can use defaultdict

    for key, value in args_keys.iteritems():
        stripped_args[key] = value.strip()

    # I don't really need a list for arguments without values, I can make their
    # values None.
    for value in args_list:
        stripped_args[value.strip()] = None

    return stripped_args


def _get_config_variable(env, variable_name, default_value):
    return env.config.get('ticketstats', variable_name, default_value)


def _get_args_defaults(env, args):
    """
    Fill the args dict with the default values for the keys that don't exist
    """
    defaults = {'height': _get_config_variable(env, 'height', 500),
                'column_width': _get_config_variable(env, 'column_width', 40),
                'res_days': _get_config_variable(env, 'res_days', 7),
                'title': _get_config_variable(env, 'default_title',
                                              'Tickets statistics'),
                'daterange': _get_config_variable(env, 'default_daterange',
                                                  '3m;'),
                }
    # Elegant :)
    defaults.update(args)
    return defaults


class TicketStatsMacro(WikiMacroBase):

    # ==[ Helper functions ]==
    def _get_num_closed_tix(self, from_date, at_date, req, ticketFilter=""):
        """Returns an integer of the number of close ticket events counted
        between from_date to at_date."""

        status_map = {
            'new': 0,
            'reopened': 0,
            'assigned': 0,
            'closed': 1,
            'edit': 0
        }

        count = 0

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        cursor.execute("""
            SELECT t.id, tc.field, tc.time, tc.oldvalue, tc.newvalue,
              t.priority
            FROM ticket_change tc
              INNER JOIN ticket t ON t.id = tc.ticket
              INNER JOIN enum p ON p.name = t.priority AND p.type = 'priority'
            WHERE tc.time > %s AND tc.time <= %s %s
            ORDER BY tc.time
            """ % (to_timestamp(from_date), to_timestamp(at_date),
                   ticketFilter))

        for tid, field, time, old, status, priority in cursor:
            if field == 'status':
                if status in ('new', 'assigned', 'reopened', 'closed', 'edit'):
                    count += status_map[status]

        return count

    def _get_num_open_tix(self, at_date, req, ticketFilter=""):
        """Returns an integer of the number of tickets currently open on that
        date."""

        status_map = {
            'new': 0,
            'reopened': 1,
            'assigned': 0,
            'closed': -1,
            'edit': 0
        }

        count = 0

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        # TODO clean up this query
        cursor.execute("""
            SELECT t.type AS type, owner, status, time AS created
            FROM ticket t
              INNER JOIN enum p ON p.name = t.priority
            WHERE p.type = 'priority' AND time <= %s %s
            """ % (to_timestamp(at_date), ticketFilter))

        for rows in cursor:
            count += 1

        cursor.execute("""
            SELECT t.id, tc.field, tc.time, tc.oldvalue, tc.newvalue,
              t.priority
            FROM ticket_change tc
              INNER JOIN ticket t ON t.id = tc.ticket
              INNER JOIN enum p ON p.name = t.priority AND p.type = 'priority'
            WHERE tc.time > 0 AND tc.time <= %s %s
            ORDER BY tc.time""" % (to_timestamp(at_date), ticketFilter))

        for tid, field, time, old, status, priority in cursor:
            if field == 'status':
                if status in ('new', 'assigned', 'reopened', 'closed', 'edit'):
                    count += status_map[status]

        return count

    def expand_macro(self, formatter, name, args):
        """

        @param formatter: 
        @param name: 
        @param args: 
        @return: 
        """
        args = _parse_args(args)
        args = _get_args_defaults(formatter.env, args)

        d_date_range = args["daterange"].split(";")
        if len(d_date_range) == 1:
            d_date_range.append("")
        from_date = _parse_relative_time(d_date_range[0] or "10y", utc)
        at_date = _parse_relative_time(d_date_range[1] or "now", utc)

        graph_res = int(args["res_days"])
        if "query" in args:
            query = args["query"]

            query_object = Query.from_string(self.env, query)
            sql_format_string, format_string_arguments = query_object.get_sql()
            # Hack to remove extra columns, I don't know another way to do it
            sql_format_string = "SELECT t.id " + \
                                sql_format_string[
                                    sql_format_string.index("FROM ticket"):]

            ticketFilter = "AND t.id IN (%s)" % \
                           (sql_format_string % tuple(format_string_arguments))
        else:
            ticketFilter = ""

        chart_title = args["title"]

        req = formatter.req

        count = []

        # Calculate 0th point
        last_date = from_date - timedelta(graph_res)
        last_num_open = self._get_num_open_tix(last_date, req, ticketFilter)

        # Calculate remaining points
        for cur_date in date_range(from_date, at_date, graph_res):
            num_open = self._get_num_open_tix(cur_date, req, ticketFilter)
            num_closed = self._get_num_closed_tix(last_date, cur_date, req,
                                                  ticketFilter)
            date = format_date(cur_date)
            if graph_res != 1:
                date = "%s thru %s" % (format_date(last_date), date)
            count.append({
                'date': date,
                'new': num_open - last_num_open + num_closed,
                'closed': num_closed,
                'open': num_open})
            last_num_open = num_open
            last_date = cur_date

        chart_data = ", \n".join(['{date: \'%(date)s\', new_tickets: %(new)d, '
                                  'closed: %(closed)d, open: %(open)d}' % d
                                  for d in count])

        data = {
            'chart_title': chart_title,
            'chart_data': chart_data,
            'height': args['height'],
            'column_width': args['column_width'],
            'id': random.randint(1, 9999999)
        }

        template = Chrome(self.env).load_template('ticketstats_macro.html')

        return template.generate(**data)

##             "chart_data": """
## {date: "from1to2", new_tickets:23, closed: 22, open:33 },
## {date: "from2to3", new_tickets:20, closed: 20, open:3 }"""})
