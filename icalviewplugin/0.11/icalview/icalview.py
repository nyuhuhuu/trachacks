"""
plugin fro Trac 0.11 to provide iCalendar ouput for ticket's queries
author : Xavier Pechoultes <x.pechoultres@clariprint.com>
Licence: GPL
"""

import os
import sys
import re
import datetime
import time
from trac.core import *
from trac.util.translation import _
from trac.util.datefmt import format_datetime,localtz
from trac.web import IRequestHandler
from trac.ticket.query import QueryModule
from trac.ticket import Milestone
from trac.mimeview.api import  IContentConverter
from trac.web.chrome import INavigationContributor
from cStringIO import StringIO
from trac.resource import Resource, get_resource_url
class iCalViewPlugin(QueryModule):
    implements(IRequestHandler, INavigationContributor, 
               IContentConverter)

    """Plugin class """

    def match_request(self, req):
        return req.path_info == '/ical'

    def convert_content(self, req, mimetype, query, key):
        return self.export_ical(req, query)

    def get_supported_conversions(self):
        yield ('ical', _('iCalendar'), 'ics',
               'trac.ticket.Query', 'text/calendar', 8)

    def convert_content(self, req, mimetype, query, key):
        if key == 'ical':
            return self.export_ical(req, query)
    
    def get_active_navigation_item(self, req):
        return 'icalendar'

    def parse_date(self,d):
        """
        parse a user date by using standard or user config formats
        use `short_date_format` and `date_time_format` config values
        different formats can be defined separated by `;`
        """
        date_format = self.config['icalendar'].get('short_date_format','%m/%d/%Y')
        date_time_format = self.config['icalendar'].get('date_time_format','%m/%d/%Y %H:%M')
        for fmt in date_format.split(";"):
            try:
                ts = time.strptime(d, fmt)
                return datetime.date(ts[0],ts[1],ts[2])
            except:
                self.env.log.debug(d + " not match " + fmt)
        for fmt in date_time_format.split(";"):
            try:
                ts = time.strptime(d, date_time_format)
                return datetime.datetime(*ts[:6])
            except:
                self.env.log.debug(d + " not match " + date_time_format)
        return None

    def parse_duration(self,d):
        """
        parse a user duration
        if the duration begin by a 'P', we presume that it math RFC specification for duration
        the user may set a number of x days (our hours) by ending the duration with a `d` (our `h`) : `2d` (`2h`)
        we support also standar H:M definition.
        """
        if d[0] == "P" :
             return d
        val = re.match("([0-9]{1,})d",d)
        if val :
           n_days = int(val.groups()[0])
           return datetime.timedelta(n_days+1)
        val = re.match("([0-9]{1,})h",d)
        if val :
           n_hours = int(val.groups()[0])
           return datetime.timedelta(0, 0,0,0, 0,n_hours)
        val = re.match("([0-9]{1,}):([0-9]{2})",d)
        if val :
           n_hours = int(val.groups()[0])
           n_minutes = int(val.groups()[1])
           return datetime.timedelta(0, 0,0,0,n_minutes,n_hours)
        return datetime.timedelta(1)
    
    def format_date(self,content,propname,d):
        if type(d) == datetime.datetime :
            content.write("%s:%s\r\n" % (propname,d.strftime("%Y%m%dT%H%M%S")))
        else:
            content.write("%s;VALUE=DATE:%s\r\n" % (propname,d.strftime("%Y%m%d")))

    def export_ical(self, req, query):        
        """
        return the icalendar file
        """
        dtstart_key = self.config['icalendar'].get('dtstart','date_start')
        duration_key = self.config['icalendar'].get('duration','duration')
        input_date_format = self.config['icalendar'].get('input_date_format','duration')

        if dtstart_key not in query.cols:
            query.cols.append(dtstart_key)
        if duration_key not in query.cols:
            query.cols.append(duration_key)
        if 'priority' not in query.cols:
            query.cols.append('priority')
        if 'description' not in query.cols:
            query.cols.append('description')
        if 'changetime' not in query.cols:
            query.cols.append('changetime')
        if 'time' not in query.cols:
            query.cols.append('time')
        query.max = sys.maxint
        results = query.execute(req)
        cols = query.get_columns()
        content = StringIO()
        content.write('BEGIN:VCALENDAR\r\n')
        content.write('VERSION:2.0\r\n')
        content.write('PRODID:2.0:-//Edgewall Software//NONSGML Trac 0.11//EN\r\n')
        content.write('METHOD:PUBLISH\r\n')
        content.write('X-WR-CALNAME: test\r\n')
        content.write('X-WR-TIMEZONE:%s\r\n' % localtz.tzname)

        attr_map = {
                    "summary" : "SUMMARY",
                    "type" :  "CATEGORIES"
                   }
        priority_map = {
                    'blocker' :  1,
                    'critical' :  2,
                    'major' : 6,
                    'minor' : 8,
                    'trivial' : 9
                    }

        custom_priority_map = self.config['icalendar'].get('priority_map',None)
        if custom_priority_map != None:
            for m in custom_priority_map.split(","):
                k = m.split(":")
                if len(k) == 2:
                    priority_map[k[0]] = int(k[1])

        for result in results:
            ticket = Resource('ticket', result['id'])
            if 'TICKET_VIEW' in req.perm(ticket):
                kind = "VEVENT"
                dtstart = self.parse_date(result[dtstart_key])
                due = None
                if dtstart == None :
                    kind = "VTODO"
                    self.env.log.debug("is TODO")
                    if result.has_key("milestone"):
                        milestone_key = result["milestone"]
                        self.env.log.debug("Milestone !" + milestone_key)
                        milestone = Milestone(self.env,milestone_key)
                        due = milestone.due
                                
                content.write("BEGIN:%s\r\n" % kind)
                content.write("UID:<%s@%s>\r\n" % (get_resource_url(self.env,ticket,req.href),os.getenv('SERVER_NAME')))
                if dtstart != None :
                    self.format_date(content,"DTSTART",dtstart)
                    duration = self.parse_duration(result[duration_key])
                    if type(duration) == datetime.timedelta :
                        content.write("DURATION:P%dDT%dS\r\n" % (duration.days, duration.seconds))
                    else :
                        content.write("DURATION:%s\r\n" % duration)
                elif due != None:
                    self.format_date(content,"DUE",due)
                content.write("CREATED:%s\r\n" % result["time"].strftime("%Y%m%dT%H%M%S"))
                content.write("DTSTAMP:%s\r\n" % result["changetime"].strftime("%Y%m%dT%H%M%S"))
                protocol = "http"
                if "HTTPS" in os.getenv('SERVER_PROTOCOL') :
                    protocol = "https"
                content.write("URL:%s://%s%s\r\n" % (protocol,os.getenv('SERVER_NAME'),get_resource_url(self.env,ticket,req.href)))
                priority = priority_map[result['priority']]
                if priority != None:
                    content.write("PRIORITY;VALUE=%s:%d\r\n" % (result['priority'],priority))

                for key in attr_map:
                   if key in cols:
                       content.write("%s:%s\r\n" % (attr_map[key], unicode(result[key]).encode('utf-8')))
                content.write("END:%s\r\n" % kind)
        content.write('END:VCALENDAR\r\n')
        return content.getvalue(), 'text/calendar;charset=utf-8'
