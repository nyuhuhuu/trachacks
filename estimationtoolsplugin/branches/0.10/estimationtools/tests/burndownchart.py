from estimationtools.burndownchart import *
from estimationtools.utils import *
from trac.test import EnvironmentStub
from trac.ticket.model import Ticket
import time
import unittest


class BurndownChartTestCase(unittest.TestCase):
    
    def setUp(self):
        self.env = EnvironmentStub(default_data = True)
        self.env.config.set('ticket-custom', 'hours_remaining', 'text')
        self.env.config.set('estimation-tools', 'estimation_field', 'hours_remaining')
        
    def _insert_ticket(self, estimation):
        ticket = Ticket(self.env)
        ticket['summary'] = 'Test Ticket'
        ticket['hours_remaining'] = estimation
        ticket['milestone'] = 'milestone1'
        return ticket.insert()

    def _change_ticket(self, id, history):
        ticket = Ticket(self.env, id)
        keys = history.keys()
        keys.sort()
        for key in keys:
            ticket['hours_remaining'] = history[key]
            ticket.save_changes("me", "testing", time.mktime(key.timetuple()))
            
    def test_parse_options(self):
        db = self.env.get_db_cnx()
        options = parse_options(db, {"milestone":"milestone1", "startdate":"2008-02-20",
                             "enddate":"2008-02-28"})
        self.assertNotEqual(options['milestone'], None)
        self.assertNotEqual(options['startdate'], None)
        self.assertNotEqual(options['enddate'], None)
        
    def test_build_empty_chart(self):
        chart = BurndownChart(self.env)
        db = self.env.get_db_cnx()
        options = parse_options(db, {"milestone":"milestone1", "startdate":"2008-02-20",
                             "enddate":"2008-02-28"})
        timetable = chart._calculate_timetable(options)
        xdata, ydata, maxhours = chart._scale_data(timetable, options)
        self.assertEqual(xdata, ['0.0', '12.5', '25.0', '37.5', '50.0', '62.5', '75.0', '87.5', '100.0'])
        self.assertEqual(ydata, ['0.0', '0.0', '0.0', '0.0', '0.0', '0.0', '0.0', '0.0', '0.0'])
        self.assertEqual(maxhours, 100.0)
        
    def test_calculate_timetable_simple(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now().date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'milestone': "milestone1", 'startdate': day1, 'enddate': day3}
        self._insert_ticket('10')
        timetable = chart._calculate_timetable(options)
        self.assertEqual(timetable, {day1: 10.0, day2: 10.0, day3: 10.0})
        
    def test_calculate_timetable_with_simple_changes(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now().date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'milestone': "milestone1", 'startdate': day1, 'enddate': day3}
        ticket1 = self._insert_ticket('10')
        self._change_ticket(ticket1, {day2:'5', day3:'0'})
     
        timetable = chart._calculate_timetable(options)
        self.assertEqual(timetable, {day1: 10.0, day2: 5.0, day3: 0.0})
        
    def test_calculate_timetable_with_simple_changes_2(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now().date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'milestone': "milestone1", 'startdate': day1, 'enddate': day3}
        ticket1 = self._insert_ticket('10')
        self._change_ticket(ticket1, {day2:'5', day3:'0'})
        ticket2 = self._insert_ticket('0')
        self._change_ticket(ticket2, {day2:'1', day3:'2'})
     
        timetable = chart._calculate_timetable(options)
        self.assertEqual(timetable, {day1: 10.0, day2: 6.0, day3: 2.0})

    def test_calculate_timetable_with_recent_changes(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now().date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        day4 = day3 + timedelta(days=1)
        options = {'today': day3, 'milestone': "milestone1", 'startdate': day1, 'enddate': day3}
        ticket1 = self._insert_ticket('10')
        self._change_ticket(ticket1, {day2:'5', day4:'0'})
     
        timetable = chart._calculate_timetable(options)
        self.assertEqual(timetable, {day1: 10.0, day2: 5.0, day3: 5.0})
