from decimal import Decimal
from datetime import datetime, timedelta
from estimationtools.burndownchart import BurndownChart
from estimationtools.utils import parse_options
from trac.test import EnvironmentStub, MockPerm, Mock
from trac.ticket.model import Ticket
from trac.util.datefmt import utc
from trac.web.href import Href
import unittest


class BurndownChartTestCase(unittest.TestCase):
    
    def setUp(self):
        self.env = EnvironmentStub(default_data = True)
        self.env.config.set('ticket-custom', 'hours_remaining', 'text')
        self.env.config.set('ticket-custom', 'hours_initial', 'text')
        self.env.config.set('estimation-tools', 'estimation_field', 'hours_remaining')
        self.env.config.set('estimation-tools', 'initial_estimation_field', 'hours_initial')
        self.req = Mock(href = Href('/'),
                        abs_href = Href('http://www.example.com/'),
                        perm = MockPerm(),
                        authname='anonymous')
        
    def _insert_ticket(self, estimation):
        ticket = Ticket(self.env)
        ticket['summary'] = 'Test Ticket'
        ticket['hours_remaining'] = estimation
        ticket['hours_initial'] = estimation
        ticket['milestone'] = 'milestone1'
        return ticket.insert()

    def _change_ticket_estimations(self, id, history):
        ticket = Ticket(self.env, id)
        keys = history.keys()
        keys.sort()
        for key in keys:
            ticket['hours_remaining'] = history[key]
            ticket.save_changes("me", "testing", datetime.combine(key, datetime.now(utc).timetz()))
    
    def _change_ticket_initial_estimations(self, id, history):
        ticket = Ticket(self.env, id)
        keys = history.keys()
        keys.sort()
        for key in keys:
            ticket['hours_initial'] = history[key]
            ticket.save_changes("me", "testing", datetime.combine(key, datetime.now(utc).timetz()))
            
    def _change_ticket_states(self, id, history):
        ticket = Ticket(self.env, id)
        keys = history.keys()
        keys.sort()
        for key in keys:
            ticket['status'] = history[key]
            ticket.save_changes("me", "testing", datetime.combine(key, datetime.now(utc).timetz()))       
            
    def test_parse_options(self):
        db = self.env.get_db_cnx()
        options, query_args = parse_options(db, "milestone=milestone1, startdate=2008-02-20, enddate=2008-02-28", {})
        self.assertNotEqual(query_args['milestone'], None)
        self.assertNotEqual(options['startdate'], None)
        self.assertNotEqual(options['enddate'], None)
        
    def test_build_empty_chart(self):
        chart = BurndownChart(self.env)
        db = self.env.get_db_cnx()
        options, query_args = parse_options(db, "milestone=milestone1, startdate=2008-02-20, enddate=2008-02-28", {})
        timetable, _ = chart._calculate_timetable(options, query_args, self.req)
        dates = sorted(timetable.keys())
        xdata, ydata, maxhours = chart._scale_data(timetable, dates, Decimal(0), options)
        self.assertEqual(xdata, ['0.00', '12.50', '25.00', '37.50', '50.00', '62.50', '75.00', '87.50', '100.00'])
        self.assertEqual(ydata, ['0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'])
        self.assertEqual(maxhours, Decimal(100))
        
    def test_build_zero_day_chart(self):
        chart = BurndownChart(self.env)
        # shouldn't throw
        chart.render_macro(self.req, "", "startdate=2008-01-01, enddate=2008-01-01")
        
    def test_calculate_timetable_simple(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3}
        query_args = {'milestone': "milestone1"}
        self._insert_ticket('10')
        timetable, _ = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(10), day3: Decimal(10)})
        
    def test_calculate_timetable_without_milestone(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3}
        self._insert_ticket('10')
        timetable, _ = chart._calculate_timetable(options, {}, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(10), day3: Decimal(10)})
        
    def test_calculate_timetable_with_simple_changes(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2:'5', day3:'0'})
     
        timetable, _ = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(5), day3: Decimal(0)})
        
    def test_calculate_timetable_with_closed_ticket(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2:'5'})
        self._change_ticket_states(ticket1, {day3: 'closed'})
        timetable, _ = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(5), day3: Decimal(0)})

    def test_calculate_timetable_with_closed_ticket2(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_states(ticket1, {day2: 'closed'})
        self._change_ticket_estimations(ticket1, {day3:'5'})
        timetable, _ = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(0), day3: Decimal(0)})

    def test_calculate_timetable_with_closed_and_reopened_ticket(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        day4 = day3 + timedelta(days=1)
        options = {'today': day4, 'startdate': day1, 'enddate': day4}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day3:'5'})
        self._change_ticket_states(ticket1, {day2: 'closed', day4: 'new'})
        timetable, _ = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(0), day3: Decimal(0), day4: Decimal(5)})
        
    def test_calculate_timetable_with_simple_changes_2(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2:'5', day3:''})
        ticket2 = self._insert_ticket('0')
        self._change_ticket_estimations(ticket2, {day2:'1', day3:'2'})
     
        timetable, _ = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(6), day3: Decimal(2)})

    def test_calculate_timetable_with_recent_changes(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        day4 = day3 + timedelta(days=1)
        options = {'today': day4, 'startdate': day1, 'enddate': day3}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2:'5', day4:''})
     
        timetable, _ = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(5), day3: Decimal(5)})
    
    def test_calculate_timetable_with_gibberish_estimates(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2: 'IGNOREME', day3:'5'})
        timetable, _ = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(10), day3: Decimal(5)})
        
    def test_calculate_delta_no_new_or_changed(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'change': True}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        self._change_ticket_estimations(ticket1, {day2:'5', day3:''})
        ticket2 = self._insert_ticket('0')
        self._change_ticket_estimations(ticket2, {day2:'1', day3:'2'})
     
        timetable, delta = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(10), day2: Decimal(6), day3: Decimal(2)})
        self.assertEqual(delta, {day1: Decimal(0), day2: Decimal(0), day3: Decimal(0)})
                
    def test_calculate_delta_with_changed_estimates(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        options = {'today': day3, 'startdate': day1, 'enddate': day3, 'change': True}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        ticket2 = self._insert_ticket('5')
        self._change_ticket_initial_estimations(ticket1, {day2:'8'}) # -2
        self._change_ticket_initial_estimations(ticket2, {day3:'8'}) # +3
        import time; time.sleep(1) # Avoid time resolution problem
        self._change_ticket_estimations(ticket2, {day2:'1', day3:'2'})
     
        timetable, delta = chart._calculate_timetable(options, query_args, self.req)
        self.assertEqual(timetable, {day1: Decimal(15), day2: Decimal(11), day3: Decimal(12)})
        self.assertEqual(delta, {day1: Decimal(0), day2: Decimal(-2), day3: Decimal(3)})
        
    def test_date_intervals(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        day4 = day3 + timedelta(days=1)
        day5 = day4 + timedelta(days=1)
        options = {'today': day5, 'startdate': day1, 'enddate': day5, 'interval_days': 2}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        ticket2 = self._insert_ticket('5')
        self._change_ticket_estimations(ticket2, {day3:'1', day4:'2', day5:'3'})

        timetable, delta = chart._calculate_timetable(options, query_args, self.req)
        
        self.assertEqual(timetable, {day1: Decimal(15), day3: Decimal(11), day5: Decimal(13)})
        self.assertEqual(delta, {day1: Decimal(0), day3: Decimal(0), day5: Decimal(0)})
    
    def test_date_intervals_always_includes_today(self):
        chart = BurndownChart(self.env)
        day1 = datetime.now(utc).date()
        day2 = day1 + timedelta(days=1)
        day3 = day2 + timedelta(days=1)
        day4 = day3 + timedelta(days=1)
        day5 = day4 + timedelta(days=1)
        day6 = day4 + timedelta(days=1)
        options = {'today': day5, 'startdate': day1, 'enddate': day5, 'interval_days': 2}
        query_args = {'milestone': "milestone1"}
        ticket1 = self._insert_ticket('10')
        ticket2 = self._insert_ticket('5')
        self._change_ticket_estimations(ticket2, {day3:'1', day4:'2', day5:'3',day6:'4'})

        timetable, delta = chart._calculate_timetable(options, query_args, self.req)
        
        self.assertEqual(timetable, {day1: Decimal(15), day3: Decimal(11), day5: Decimal(13), day6: Decimal(14)})
        self.assertEqual(delta, {day1: Decimal(0), day3: Decimal(0), day5: Decimal(0), day6: Decimal(0)})