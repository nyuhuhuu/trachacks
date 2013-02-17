# vim: set sw=4 et ts=4:
#
# -*- coding: utf-8 -*-
#
# jqplot based chart macro for trac.
#
# License: BSD

import re
import datetime
import json
import decimal

from StringIO import StringIO
from types import *

from trac.core import Component, implements
from trac.web.api import IRequestFilter
from trac.web.chrome import ITemplateProvider, add_script, add_stylesheet
from trac.wiki.macros import WikiMacroBase

from trac.util.datefmt import to_datetime

from trac.ticket.query import Query
from trac.ticket.query import TicketQueryMacro

class DecimalEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, decimal.Decimal):
            return float(value)
        super(DecimalEncoder, self).default(value)


""" Runs a query
"""
class QueryRunner(object):

    """
    current_user: the currently logged in user.

    base_url: the trac base url, used to generate links that point to different
    elements in trac, like reports and tickets.

    report_id: the id of an existing report. If none, the runner will use
    the query parameter.
    
    query: a string with the sql query to execute, only used if report_id is
    none. It may contain {number}, where number is a report id. In that case,
    {number} is replaced with the content of the report with id number.

    series_column: the name of a column that specifies a series name.
    """
    def __init__(self, env, current_user, base_url, report_id, query,
            series_column):
        self.env = env
        self.current_user = current_user
        self.query = query
        self.series_column = series_column
        self.base_url = base_url
        self.report_id = report_id

    """ Gets the sql query string and parameters to execute.
    """
    def get_query(self):

        result = [self.query, {}]
        if self.report_id is not None:
            result = self.get_query_from_report(self.report_id)

        result[0] = result[0].replace('$USER', "'" + self.current_user + "'")

        return result

    """ Returns the sql query string and parameters from a report.
    """
    def get_query_from_report(self, report_id):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        report_query = 'select query from report where id = %s' % report_id
        cursor.execute(report_query)
        for row_number, row in enumerate(cursor):
            query_string = row[0]

        if query_string[0] == '?' or query_string.startswith('query:'):
            # This is a TracQuery, not sql.
            query_string = ''.join([line.strip()
                for line in query_string.splitlines()]) 
            if query_string.startswith('query:'):
                query_string = query_string[6:]
            if query_string[0] == '?':
                query_string = query_string[1:]

            query = Query.from_string(self.env, query_string) 
            result = query.get_sql()
        else:
            result = [query_string, {}]

        self.env.log.info(result)
        return result

    """
    Runs the query and returns a DataSet.

    count_only: if this is true, the query will be a count(*) of the provided
    query. Only applies if the query is based on a report. It is mainly used to
    count the number of records in a MeterGauge.
    """
    def run(self, count_only):
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        query, params = self.get_query()
        if count_only and self.report_id is not None:
            query = "select count(*) from (" + query + ") as q"
        cursor.execute(query, params)

        use_date_axis = 'false';

        number_of_columns = len(cursor.description);

        data_set = DataSet()

        series_name = 0

        number_of_series = 0;

        for description in cursor.description:
            column_name = description[0]
            column_type = self.determine_type(column_name)

            if self.series_column != column_name and column_type != "ticket_id":
                number_of_series += 1

        if number_of_series == 0:
            number_of_series = len(cursor.description)

        for row_number, row in enumerate(cursor):
            datapoint = []
            series_name = 0
            xvalue = None
            yvalue = None
            ticket_id = None
            tooltip = ""
            link = ''

            for column_number, cell in enumerate(row):

                column_name = cursor.description[column_number][0]
                column_type = self.determine_type(column_name)

                value = self.format_cell(column_name, cell)

                if number_of_columns == 1:
                    # Just one column in the query, just add values in one
                    # series.
                    data_set.add_value(0, value)

                elif self.series_column == column_name:
                    series_name = value

                elif xvalue is None:
                    # The x axis.
                    if column_type == 'time':
                        data_set.use_date_axis()
                    xvalue = value
                    pass

                else:
                    if column_type == 'ticket_id':
                        ticket_id = value

                    if ticket_id is not None:
                        link = self.base_url + 'ticket/' + str(ticket_id)

                    if self.series_column is not None:
                        tooltip = series_name
                        if column_type != 'ticket_id':
                            yvalue = value
                    else:
                        data_set.add_point(series_name, xvalue, value, tooltip,
                                link)
                        series_name += 1

            if self.series_column is not None:
                data_set.add_point(series_name, xvalue, yvalue, tooltip, link)

        return data_set

    """
    If this query corresponds to a report, this returns the link to go to that
    report. Otherwise, it returns None.
    """
    def get_report_link(self):
        if self.report_id is not None:
            return 'report/' + str(self.report_id)

    """
    Formats the cell according to its column name. This is consistent with
    trac, which is reasonable given that it can be used with sqlite, which is
    typeless.

    name: the name of the column. See determine_type for the supported column
    names.

    value: the value to format.
    """
    def format_cell(self, name, value):

        value_type = self.determine_type(name)
        if value_type == 'time':
            return to_datetime(value).strftime('%Y-%m-%d')
        if value_type == 'date':
            return str(to_datetime(value));
        if type(value) == StringType or type(value) == UnicodeType:
            return str(value)
        else:
            return value

    """
    Determines the type based on the column name, just like trac.

    ticket - Ticket ID number. Becomes a hyperlink to that ticket.

    id - same as ticket above when realm is not set

    realm - together with id, can be used to create links to other resources
    than tickets (e.g. a realm of wiki and an id to a page name will create a
    link to that wiki page)

    created, modified, date, time - Format cell as a date and/or time.

    *_time - considered a time.

    *_date - considered a date.

    Any other column name is treated as string.
    """
    def determine_type(self, name):
        if name == 'ticket' or name == 'id':
            return 'ticket_id'
        if name == 'created' or name == 'modified' or name == 'date':
            return 'date'
        if name == 'time':
            return 'time'
        if name.endswith('_date'):
            return 'date'
        if name.endswith('_time'):
            return 'time'


class JQChartMacro(WikiMacroBase):
    """JQChart based chart macro.

    {{{
    #!JQChart

    # data is a list of series. A series is a sequence of data points.

    # An axis is the vertical or horizontal line with ticks.

    # You can obtain the data and the axes from the query.

    # By default, the first column from the query result is the x axis. Each of
    # the following columns correspond to one additional series.

    type : bar,

    query : "SELECT GOES HERE", If one column is a ticket id, the chart will
    have a link to the ticket. You can use {report_id} as a subselect from
    a report.

    series_column : a column name that marks a series. All rows with the same
    series_column belong to the same series. If this is specified, each row
    must have two additional columns for the x and y values respectively. You
    can add one more column for the tooltip.

    data : (not implemented yet)

    options : jqplot additional options. See jqplot documentation. For example:
       { title : 'some chart title' }
    There is an additional non jqplot entry: "gaugeClickLocation", that is a
    location to go if you click on a gauge.
    }}}

    """
    implements(IRequestFilter, ITemplateProvider)

    def expand_macro(self, formatter, name, content):
        json_string = ''
        for line in content.split('\n'):
            line = line.strip()
            if re.match('^\s*#', line) or re.match('^\s*$', line):
                continue
            json_string += ' ' + line

        json_object = json.loads('{' + json_string + '}')

        buf = StringIO()

        id_generator = ChartIdGenerator(formatter.context)

        query = json_object.get("query", None)
        report_id = json_object.get("report_id", None)
        options = json_object.get("options", None)
        chart_type = json_object.get("type", "Line")

        default_width = 500
        default_height = 300
        if chart_type == 'MeterGauge':
            default_width = 150
            default_height = 120

        width = json_object.get("width", default_width)
        height = json_object.get("height", default_height)

        self.env.log.info(width)
        self.env.log.info(height)

        series_column = json_object.get("series_column", None)

        base_url = formatter.req.href('')
        current_user = formatter.req.authname
        query_runner = QueryRunner(self.env, current_user, base_url, report_id,
                query, series_column)

        chart = Chart(formatter.req, id_generator.get_id(), width, height)
        chart.render(self.env, chart_type, options, query_runner, buf)
        return buf.getvalue()

    # ITemplateProvider methods
    def get_templates_dirs(self):
        return []
    
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('jqplotchart', resource_filename(__name__, 'htdocs'))]

    # IRequestFilter#pre_process_request
    def pre_process_request(self, req, handler):
        return handler

    # IRequestFilter#post_process_request
    def post_process_request(self, req, template, data, content_type):

        add_stylesheet (req, 'jqplotchart/jqplot/jquery.jqplot.min.css')
        add_stylesheet (req, 'jqplotchart/jqchart.css')

        add_script (req, 'jqplotchart/jqplot/jquery.jqplot.min.js')

        plugin_base = 'jqplotchart/jqplot/plugins/jqplot.'
        add_script (req, plugin_base + 'highlighter.min.js')
        add_script (req, plugin_base + 'cursor.min.js')
        add_script (req, plugin_base + 'dateAxisRenderer.min.js')
        add_script (req, plugin_base + 'categoryAxisRenderer.min.js')
        add_script (req, plugin_base + 'pointLabels.min.js')
        add_script (req, plugin_base + 'pieRenderer.min.js')
        add_script (req, plugin_base + 'donutRenderer.min.js')
        add_script (req, plugin_base + 'barRenderer.min.js')
        add_script (req, plugin_base + 'meterGaugeRenderer.min.js')
        add_script (req, 'jqplotchart/jqchart.js')

        return (template, data, content_type)

"""
Generates a unique id for the dom element that contains the chart.

"""
class ChartIdGenerator(object):
    
    """
    context: the trac request context, used to store the current id.
    """
    def __init__(self, context):
        self.context = context

    """
    get_id: returns a unique id each time it is called.
    """
    def get_id(self):
        index = self.context.get_hint('jqplotchart_index')
        if (self.context.has_hint('jqplotchart_index')):
            index = self.context.get_hint('jqplotchart_index')
        else:
            index = 0
        index += 1
        self.context.set_hints(jqplotchart_index = index)

        return "jqplotchartplugin-" + str(index)

"""
datasets: the resulting data set, an arry of series, each series is an array of
points.

additional_info: an array of series, each series is an array of [tooltip, url].
"""
class DataSet(object):

    def __init__(self):
        self.datasets = []
        self.additional_info = []
        self.name_to_index = {}
        self.uses_date_axis = False

        self.legends = []

    def use_date_axis(self):
        self.uses_date_axis = True

    """ Adds a new value to a series.

    This is used when there is just one column in the query.

    series: an integer with the series number.
    """
    def add_value(self, series, x):
        if len(self.datasets) <= series:
            self.datasets.append([])
        self.datasets[series].append([len(self.datasets[series]), x])

    """ Adds a point to a series.

    series_name the name of the series to add the point to.

    x: the x value of the series.

    y: the y value of the series.

    tooltip: the tooltip to show on mouse over. None if you don't want a
    tooltip.

    click_url: the url to go if the user clicks on a point.
    """
    def add_point(self, series_name, x, y, tooltip, click_url):

        if series_name not in self.name_to_index:
            self.name_to_index[series_name] = len(self.name_to_index)
            self.legends.append({"label": series_name})

        series = self.name_to_index[series_name]
        if len(self.datasets) <= series:
            self.datasets.append([])
            self.additional_info.append([])
        self.datasets[series].append([x, y])
        self.additional_info[series].append([tooltip, click_url])

    """
    """
    def get_datasets(self):
        return self.datasets

    def get_additional_info(self):
        return self.additional_info

    """
    Obtains the jqplot chart options.
    """
    def get_options(self):
        if len(self.legends) != 0:
            options = {}
            options["series"] = self.legends
            return options
        else:
            return None

    """ Returns "true" or "false" (a string) if we use a date axis.
    """
    def get_use_date_axis(self):
        if self.uses_date_axis:
            return "true"
        else:
            return "false"

class Chart(object):

    def __init__(self, req, chart_id, width, height):
        self.width = width
        self.height = height
        self.req = req
        self.chart_id = chart_id

    """ Executes the query and returns the dataset, an instance of DataSet.

    data.datasets
    data.use_date_axis
    data.additional_options

    data.datasets: contains the list of series. Each series is a sequece of
    'points' of the form [x, y, tooltip, link].
    """
    def run_query_TRAC_QUERY(self, env, query, series_column):

        use_date_axis = 'false';

        data = query.execute()
        column_names = query.get_columns()
        number_of_columns = len(column_names);

        data_set = DataSet()

        series_name = 0

        number_of_series = 0;

        for column_name in column_names:
            column_type = self.determine_type(column_name)

            if series_column != column_name and column_type != "ticket_id":
                number_of_series += 1

        if number_of_series == 0:
            number_of_series = len(column_names)

        for row_number, row in enumerate(data):
            datapoint = []
            series_name = 0
            xvalue = None
            yvalue = None
            ticket_id = None
            tooltip = ""
            link = ''

            for column_index, column_name in enumerate(column_names):

                column_type = self.determine_type(column_name)
                cell = data[row_number][column_name]
                value = self.format_cell(column_name, cell)

                if number_of_columns == 1:
                    # Just one column in the query, just add values in one
                    # series.
                    data_set.add_value(0, value)

                elif series_column == column_name:
                    series_name = value

                elif xvalue is None:
                    # The x axis.
                    if column_type == 'time':
                        data_set.use_date_axis()
                    xvalue = value
                    pass

                else:
                    if column_type == 'ticket_id':
                        ticket_id = value

                    if ticket_id is not None:
                        link = self.req.href('ticket/' + str(ticket_id))

                    if series_column is not None:
                        tooltip = series_name

                    if series_column is None:
                        data_set.add_point(series_name, xvalue, value, tooltip,
                                link)
                        series_name += 1

                    elif column_type != 'ticket_id':
                        yvalue = value

            if series_column is not None:
                data_set.add_point(series_name, xvalue, yvalue, tooltip, link)

        return data_set

    """
    Renders the output.

    env: the trac environment.

    chart_type: the chart type. Donut, Pie, Line, Bar or MeterGauge.

    options: the chart options. See jqplot for the elements.

    query {string}: the sql query to execute.

    buf {StringIO}: the place to write the output.

    """
    def render(self, env, chart_type, options, query_runner, buf):

        jqplot_options = {"baseUrl": self.req.href()}

        count_only = False
        if chart_type == 'MeterGauge':
            count_only = True
            if 'gaugeClickLocation' not in options:
                options['gaugeClickLocation'] = query_runner.get_report_link()

        # Run the sql statement and creates a DataSet object.
        data = query_runner.run(count_only)

        datasets = data.get_datasets()
        additional_info = data.get_additional_info()
        use_date_axis = data.get_use_date_axis()


        if options is not None:
            jqplot_options.update(options)

        dataset_options = data.get_options()
        if dataset_options is not None:
           jqplot_options.update(dataset_options)
        options_str = json.dumps(jqplot_options, cls = DecimalEncoder)

        datasets_str = json.dumps(datasets, cls = DecimalEncoder)
        additional_info_str = json.dumps(additional_info, cls = DecimalEncoder)

        buf.write("<script type='text/javascript'>\n")
        buf.write(
              "jQuery(document).ready(function() {\n"
            + "  var series = " + datasets_str + ";\n"
            + "  var additionalInfo = " + additional_info_str + ";\n"
            + "  var containerId = '" + self.chart_id + "';\n"
            + "  var chartType = '" + chart_type + "';\n"
            + "  var baseOptions = " + options_str + ";\n"
            + "  var useDateAxis = " + str(use_date_axis) + ";\n"
            + "  renderChart(containerId, chartType, series, additionalInfo, "
            +      "useDateAxis, baseOptions);\n"
            + "});\n")
        buf.write("</script>\n")

        buf.write("<div style='display: inline-block;'>")
        buf.write("<div id='" + self.chart_id
            + "' style='height:" + str(self.height) + "px; width:"
            + str(self.width) + "px;'></div>")
        buf.write("</div>")

