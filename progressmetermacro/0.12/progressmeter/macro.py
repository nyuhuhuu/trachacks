# -*- coding: utf-8 -*-

import os
import re

from trac.config import ExtensionOption, ExtensionPoint
from trac.core import *
from trac.ticket.query import Query
from trac.ticket.roadmap import ITicketGroupStatsProvider, \
                                apply_ticket_permissions, get_ticket_stats
from trac.util import TracError
from trac.web.chrome import Chrome, ITemplateProvider, add_stylesheet
from trac.wiki.api import IWikiMacroProvider, parse_args
from trac.wiki.macros import WikiMacroBase


def query_stats_data(req, stat, constraints, grouped_by='component',
                     group=None):
    def query_href(extra_args):
        args = {grouped_by: group, 'group': 'status', 'order': 'priority'}
        args.update(constraints)
        args.update(extra_args)
        return req.href.query(args)
    return {'stats': stat,
            'stats_href': query_href(stat.qry_args),
            'interval_hrefs': [query_href(interval['qry_args'])
                               for interval in stat.intervals]}

class ProgressMeterMacro(WikiMacroBase):
    """Progress meter wiki macro plugin for Trac

    Usage instructions are available at:
        http://trac-hacks.org/wiki/ProgressMeterMacro
    """
    implements(ITemplateProvider)

    _sp = ExtensionOption('progressmeter', 'stats_provider',
                          ITicketGroupStatsProvider,
                          'DefaultTicketGroupStatsProvider',
        """Name of the component implementing `ITicketGroupStatsProvider`,
        which is used to collect statistics on groups of tickets
        for meters generated by the ProgressMeterMacro plugin.""")

    _ticket_re = re.compile(r'/ticket/([0-9]+)$')
    def _this_ticket(self, req):
        match = self._ticket_re.match(req.path_info)
        if match:
            return match.group(1)
        else:
            assert req.path_info == '/newticket', "The `self` " \
              "keyword is permitted in ticket descriptions only."
            return None

    def _parse_macro_content(self, content, req):
        args, kwargs = parse_args(content, strict=False)
        kwargs['max'] = 0
        kwargs['order'] = 'id'
        kwargs['col'] = 'id'

        # special case for values equal to 'self': replace with current ticket
        # number, if available
        preview = False
        for key in kwargs.keys():
            if kwargs[key] == 'self':
                current_ticket = self._this_ticket(req)
                if current_ticket:
                    kwargs[key] = current_ticket
                else:
                    # id=0 basically causes a dummy preview of the meter
                    # to be rendered
                    preview = True
                    kwargs = {'id': 0}
                    break

        try:
            spkw = kwargs.pop('stats_provider')
            xtnpt = ExtensionPoint(ITicketGroupStatsProvider)

            found = False
            for impl in xtnpt.extensions(self):
                if impl.__class__.__name__ == spkw:
                    found = True
                    stats_provider = impl
                    break

            if not found:
                raise TracError("Supplied stats provider does not exist!")
        except KeyError:
            # if the `stats_provider` keyword argument is not provided,
            # propagate the stats provider defined in the config file
            stats_provider = self._sp

        return stats_provider, kwargs, preview

    def expand_macro(self, formatter, name, content):
        req = formatter.req
        stats_provider, kwargs, preview = self._parse_macro_content(content, req)

        # Create & execute the query string
        qstr = '&'.join(['%s=%s' % item
                               for item in kwargs.iteritems()])
        query = Query.from_string(self.env, qstr)
        try:
            # XXX: simplification, may cause problems with more complex queries
            constraints = query.constraints[0]
        except IndexError:
            constraints = {}

        # Calculate stats
        qres = query.execute(req)
        tickets = apply_ticket_permissions(self.env, req, qres)

        stats = get_ticket_stats(stats_provider, tickets)
        stats_data = query_stats_data(req, stats, constraints)

        # ... and finally display them
        add_stylesheet(req, 'common/css/roadmap.css')
        chrome = Chrome(self.env)
        stats_data.update({'preview': preview})     # displaying a preview?
        return chrome.render_template(req, 'progressmeter.html', stats_data,
                                      fragment=True)

    ## ITemplateProvider methods
    def get_htdocs_dirs(self):
        return []

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
