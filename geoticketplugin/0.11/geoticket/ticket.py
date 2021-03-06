"""
GeoTicket:
a plugin for Trac to geolocate issues
http://trac.edgewall.org
"""

import geopy
import simplejson

from customfieldprovider import ICustomFieldProvider
from genshi.builder import tag
from genshi.builder import Markup
from genshi.filters import Transformer
from genshi.template import TemplateLoader
from geoticket.interface import IMapMarkerStyle
from geoticket.options import FloatOption
from pkg_resources import resource_filename
from trac.config import BoolOption
from trac.config import ListOption
from trac.config import Option
from trac.config import OrderedExtensionsOption
from trac.core import *
from trac.db import Table, Column, Index
from trac.db.postgres_backend import PostgreSQLConnection
from trac.env import IEnvironmentSetupParticipant
from trac.ticket.api import ITicketChangeListener
from trac.ticket.api import ITicketManipulator
from trac.ticket.model import Ticket
from trac.web.api import IRequestFilter
from trac.web.api import IRequestHandler
from trac.web.api import ITemplateStreamFilter
from trac.web.chrome import add_script
from trac.web.chrome import Chrome
from trac.web.chrome import ITemplateProvider
from tracsqlhelper import create_table
from tracsqlhelper import execute_non_query
from tracsqlhelper import get_all_dict
from tracsqlhelper import get_column
from tracsqlhelper import get_first_row
from tracsqlhelper import get_scalar

templates_dir = resource_filename(__name__, 'templates')

class GeolocationException(Exception):
    """error for multiple and unfound locations"""
    

    def __init__(self, location='', locations=()):
        Exception.__init__(self, location, locations)
        self.location = location
        self.locations = locations
    
    def __str__(self):
        if self.locations:
            return self.multiple_locations()
        else:
            if self.location.strip(): 
                return "%s could not be located" % self.location
            else:
                return "No location"

    def multiple_locations(self, html=False):
        err = "Multiple locations found for %s:" % self.location
        if html:
            locations = ['<a href="?location=%s&latitude=%s&longitude=%s">%s</a>' % (i[0],i[1][0], i[1][1], i[0])
                         for i in self.locations ]
            err += '<ul class="geolocation_error"><li>' + '</li><li>'.join(locations) + '</li></ul>'
        else:
            err += '; '.join([i[0] for i in self.locations])
        return err
                                                 

    def html(self):
        if not self.locations:
            return str(self)
        return self.multiple_locations(html=True)


class GeoTicket(Component):

    implements(ICustomFieldProvider, 
               ITicketManipulator, 
               ITicketChangeListener, 
               IRequestFilter,
               IRequestHandler,
               ITemplateProvider,
               ITemplateStreamFilter,
               IEnvironmentSetupParticipant)

    ### configuration options
    mandatory_location = BoolOption('geo', 'mandatory_location', 'false',
                                    "Enforce a mandatory and valid location field")
    google_api_key = Option('geo', 'google_api_key', '',
                            "Google maps API key, available at http://code.google.com/apis/maps/signup.html")
    wms_url = Option('geo', 'wms_url',
                     'http://maps.opengeo.org/geowebcache/service/wms',
                     "URL for the WMS")
    openlayers_url = Option('geo', 'openlayers_url', 
                            'http://openlayers.org/api/2.8-rc2/OpenLayers.js',
                            "URL of OpenLayers JS to use")

    # default viewing frame lat/lon
    min_lat = FloatOption('geo', 'min_lat', '-85.',
                          "minimum latitude for default map display")
    max_lat = FloatOption('geo', 'max_lat', '85.',
                          "maximum latitude for default map display")
    min_lon = FloatOption('geo', 'min_lon', '-180.',
                          "minimum longitude for default map display")
    max_lon = FloatOption('geo', 'max_lon', '180.',
                          "maximum longitude for default map display")

    # options for customizing map display
    feature_popup = Option('geo', 'feature_popup', '',
                           "template for map feature popup")
    marker_style = OrderedExtensionsOption('geo', 'marker_style', IMapMarkerStyle, '',
                                           include_missing=False,
                                           doc="components to use to set feature style")

    ### method for ICustomFieldProvider

    # TODO : ensure CustomFieldProvider is enabled
    # XXX or, should CustomFieldProvider be used at all?
    def fields(self):
        return { 'location': None }

    ### methods for ITicketManipulator

    def prepare_ticket(self, req, ticket, fields, actions):
        """Not currently called, but should be provided for future
        compatibility."""

    def validate_ticket(self, req, ticket):
        """Validate a ticket after it's been populated from user input.
        
        Must return a list of `(field, message)` tuples, one for each problem
        detected. `field` can be `None` to indicate an overall problem with the
        ticket. Therefore, a return value of `[]` means everything is OK."""

        location_changed = True

        # check for latitude and longitude in the request
        if 'latitude' in req.args and 'longitude' in req.args:
            lat = float(req.args['latitude'])
            lon = float(req.args['longitude'])
        else:
            lat = lon = None
            # compare ticket['location'] with stored version for existing tickets
            if ticket.id:
                location_changed = not ticket['location'] == Ticket(self.env, ticket.id)['location']

        
        # get location string
        location = ticket['location']
        if location is None:
            location = ''
        location = location.strip()

        # enforce the location field, if applicable
        if not location:
            if location_changed and ticket.id:
                self.delete_location(ticket.id)
            if self.mandatory_location:
                return [('location', 'Please enter a location')]
            else:
                return []

        # do nothing if the location isn't changed
        if not location_changed: 
            return []

        # XXX blindly assume UTF-8
        try:
            location = location.encode('utf-8')
        except UnicodeEncodeError:
            raise
        
        # geolocate the address
        if lat is not None and lon is not None:
            if ticket.id:
                self.set_location(ticket.id, lat, lon)
            else:
                # XXX what if not ticket.id ?
                ticket.latitude = lat
                ticket.longitude = lon
        else:
            try:
                ticket['location'], (lat, lon) = self.geolocate(location)
                if ticket.id:
                    self.set_location(ticket.id, lat, lon)
            except GeolocationException, e:
                if location_changed and ticket.id:
                    self.delete_location(ticket.id)
                if len(e.locations) > 1:
                    return [('location', str(e))]
                if self.mandatory_location:
                    return [('location', str(e))]

                # store the error in a cookie as add_warning is clobbered
                # in the post-POST redirect
                req.session['geolocation_error'] = e.html()
                req.session.save()

        return []


    ### methods for ITicketChangeListener

    """Extension point interface for components that require notification
    when tickets are created, modified, or deleted."""

    def ticket_changed(self, ticket, comment, author, old_values):
        """Called when a ticket is modified.
        
        `old_values` is a dictionary containing the previous values of the
        fields that have changed.
        """

    def ticket_created(self, ticket):
        """Called when a ticket is created."""
        # TODO : could cache the geolocation in memory
        # instead of geolocating twice (once here and once in
        # ITicketManipulator)
        if hasattr(ticket, 'latitude') and hasattr(ticket, 'longitude'):
            self.set_location(ticket.id, ticket.latitude, ticket.longitude)
        else:

            try:
                location, (lat, lon) = self.locate_ticket(ticket)
                self.set_location(ticket.id, lat, lon)
            except GeolocationException:
                pass

    def ticket_deleted(self, ticket):
        """Called when a ticket is deleted."""
        # remove extraneous location data;
        # a new ticket could be made with the same id
        self.delete_location(ticket.id)


    ### methods for IRequestFilter

    """Extension point interface for components that want to filter HTTP
    requests, before and/or after they are processed by the main handler."""

    def post_process_request(self, req, template, data, content_type):
        """Do any post-processing the request might need; typically adding
        values to the template `data` dictionary, or changing template or
        mime type.
        
        `data` may be update in place.

        Always returns a tuple of (template, data, content_type), even if
        unchanged.

        Note that `template`, `data`, `content_type` will be `None` if:
         - called when processing an error page
         - the default request handler did not return any result

        (Since 0.11)
        """

        # add necessary JS
        if template in ['ticket.html', 'query.html', 'report_view.html', 'wiki_view.html']:

            # add_script doesn't use URLs, so add OpenLayers script manually
            scripts = req.chrome.setdefault('scripts', [])
            scripts.append({'href': self.openlayers_url, 
                            'type': 'text/javascript'})
            add_script(req, 'geoticket/js/query.js')
            add_script(req, 'geoticket/js/mapscript.js')

        # filter for tickets
        if template == 'ticket.html':
            add_script(req, 'geoticket/js/location_filler.js')
            add_script(req, 'geoticket/js/reverse_geocode.js')
            try:
                address, (latitude, longitude) = self.locate_ticket(data['ticket'])
                data['locations'] = [ {'latitude': latitude,
                                       'longitude': longitude, }]
            except GeolocationException:
                data['locations'] = []
                
        # filter for queries
        if template == 'query.html':
            # add the located tickets to a map
            tickets = [ i['id'] for i in data['tickets'] ]
            data['locations'] = self.locate_tickets(tickets, req)

        if template == 'report_view.html':
            if  req.path_info.strip('/') != 'report':
                tickets = set([])
                for group in data['row_groups']:
                    for row in group[1]:
                        if row.has_key('id'):
                            tickets.add(row['id'])
                data['locations'] = self.locate_tickets(tickets, req)
            else:
                data['locations'] = []

        return (template, data, content_type)

    def pre_process_request(self, req, handler):
        """Called after initial handler selection, and can be used to change
        the selected handler or redirect request.
        
        Always returns the request handler, even if unchanged.
        """
        return handler


    ### methods for IRequestHandler

    """Extension point interface for request handlers."""

    def match_request(self, req):
        """Return whether the handler wants to process the given request."""
        if req.path_info in ['/locate', '/reverse-locate']:
            return True

    def process_request(self, req):
        """Process the request. For ClearSilver, return a (template_name,
        content_type) tuple, where `template` is the ClearSilver template to use
        (either a `neo_cs.CS` object, or the file name of the template), and
        `content_type` is the MIME type of the content. For Genshi, return a
        (template_name, data, content_type) tuple, where `data` is a dictionary
        of substitutions for the template.

        For both templating systems, "text/html" is assumed if `content_type` is
        `None`.

        Note that if template processing should not occur, this method can
        simply send the response itself and not return anything.
        """
        content_type = 'application/json'

        # geolocation
        if req.path_info == '/locate':
            location = req.args.get('location', '')
            try:
                loc, (lat, lon) = self.geolocate(location)
                locations = {'locations': [ { 'address': loc,
                                              'latitude': lat,
                                              'longitude': lon, } ]}
            except GeolocationException, e:
                locations = e.locations
                locations = {'locations': [ { 'address': location[0],
                                              'latitude': location[1][0],
                                              'longitude': location[1][1] }
                                            for location in locations ],
                             'error': e.html()}
            req.send(simplejson.dumps(locations), content_type=content_type)

        # reverse geolocation
        if req.path_info == '/reverse-locate':
            try:
                lat, lon = req.args['latitude'], req.args['longitude']
                lat, lon = float(lat), float(lon)
                location, (lat, lon) = self.reverse_geolocate(lat, lon)
                data = {'location': { 'address': location,
                                      'latitude': lat,
                                      'longitude': lon } }
            except (KeyError, ValueError), e:
                data = {'error': str(e) }
            req.send(simplejson.dumps(data), content_type=content_type)
                

    ### methods for ITemplateProvider

    def get_htdocs_dirs(self):
        """Return a list of directories with static resources (such as style
        sheets, images, etc.)

        Each item in the list must be a `(prefix, abspath)` tuple. The
        `prefix` part defines the path in the URL that requests to these
        resources are prefixed with.
        
        The `abspath` is the absolute path to the directory containing the
        resources on the local file system.
        """
        return [('geoticket', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        """Return a list of directories containing the provided template
        files.
        """
        return [templates_dir]

    ### methods for ITemplateStreamFilter

    """Filter a Genshi event stream prior to rendering."""

    def filter_stream(self, req, method, filename, stream, data):
        """Return a filtered Genshi event stream, or the original unfiltered
        stream if no match.

        `req` is the current request object, `method` is the Genshi render
        method (xml, xhtml or text), `filename` is the filename of the template
        to be rendered, `stream` is the event stream and `data` is the data for
        the current template.

        See the Genshi documentation for more information.
        """
        if filename in ['ticket.html', 'query.html', 'report_view.html', 'mapdashboard.html', 'regions_admin.html', 'wiki_view.html']:

            # XXX random E fix for minimum lattitude that somehow
            # works and I have no idea why
            min_lat = max(-89.999999999, self.min_lat)

            chrome = Chrome(self.env)
            _data = dict(req=req, 
                         wms_url=self.wms_url,
                         min_lat=min_lat,
                         max_lat=self.max_lat,
                         min_lon=self.min_lon,
                         max_lon=self.max_lon)
            template = chrome.load_template('layers.html')
            stream |= Transformer("//script[@src='%s']" % self.openlayers_url).after(template.generate(**_data))

        return stream

    
    ### methods for IEnvironmentSetupParticipant

    """Extension point interface for components that need to participate in the
    creation and upgrading of Trac environments, for example to create
    additional database tables."""

    def environment_created(self):
        """Called when a new Trac environment is created."""
        if self.environment_needs_upgrade(None):
            self.upgrade_environment(None)

    def environment_needs_upgrade(self, db):
        """Called when Trac checks whether the environment needs to be upgraded.
        
        Should return `True` if this participant needs an upgrade to be
        performed, `False` otherwise.
        """
        if db is not None:
            db.commit() # XXX if I don't have this line, get InteralError: current transaction aborted
        return not self.version()

    def upgrade_environment(self, db):
        """Actually perform an environment upgrade.
        
        Implementations of this method should not commit any database
        transactions. This is done implicitly after all participants have
        performed the upgrades they need without an error being raised.
        """

        # create a table for ticket location
        ticket_location_table = Table('ticket_location', key='ticket')[
            Column('ticket', type='int'),
            Column('latitude', type='float'),
            Column('longitude', type='float'),
            Index(['ticket'])]
        create_table(self.env, ticket_location_table)
    
        # update ticket locations
        tickets = get_column(self.env, 'ticket', 'id')
        tickets = [ Ticket(self.env, ticket) for ticket in tickets ]
        for ticket in tickets:
            try:
                location, (lat, lon) = self.locate_ticket(ticket)
                self.set_location(ticket.id, lat, lon)
            except GeolocationException:
                pass

        # note the DB version
        execute_non_query(self.env, "insert into system (name, value) values ('geoticket.db_version', '1');")


        # add a default dashboard panel
        self.default_dashboard()

    def default_dashboard(self):
        """
        add a default dashboard viewport; 
        'activeissues' comes from the `[geo] dashboard` default,
        set in the MapDashboard component (from `web_ui.py`)
        """

        viewport = { 'activeissues.label': 'Active Issues',
                     'activeissues.query': 'location!=&status!=closed&order=changetime&desc=1' }

        if self.env.config.get('geo', 'dashboard') == 'activeissues' and sum([self.env.config.has_option('geo', key) for key in viewport]) == len(viewport):
            for key, value in viewport.items():
                self.env.config.set('geo', key, value)
                self.env.config.set('geo', key, value)

    def version(self):
        """returns version of the database (an int)"""
        version = get_scalar(self.env, "select value from system where name = 'geoticket.db_version';")
        if version:
            return int(version)
        return 0

    ### PostGIS

    def postgis_enabled(self):
        """is PostGIS enabled on the database?"""

        cnx = self.env.get_db_cnx()

        # test if connection type is PostgreSQL
        if not cnx.cnx.__class__ == PostgreSQLConnection:
            return False

        # test if PostGIS is enabled on the DB
        # from http://mateusz.loskot.net/2009/04/09/making-postgis-database/
        # psql -d trac_anothergeoproj -t -c "SELECT postgis_version();"
        cur = cnx.cursor()
        try:
            cur.execute("SELECT postgis_version();")
        except Exception, e: 
            # XXX bare Exception used
            # the actual error reached is psycopg2.ProgrammingError
            # but this might be too specific
            return False
        return bool(cur.fetchall())

    ### geolocation

    def reverse_geolocate(self, lat, lon):

        # get the geocoder
        if self.google_api_key:
            geocoder = geopy.geocoders.Google(self.google_api_key)
        else:
            geocoder = geopy.geocoders.Google()

        try:
            location, (lat, lon) = geocoder.reverse((lat, lon))
        except:
            # XXX dunno what to do
            raise
        return (location, (lat, lon))
    
    def geolocate(self, location):

        # use lat, lon if the format fits
        if location.count(',') == 1:
            lat, lon = location.split(',')
            try:
                lat, lon = float(lat), float(lon)
                if (-90. < lat < 90.) and (-180. < lon < 180.):
                    # reverse geocoding
                    try:
                        return self.reverse_geolocate(lat, lon)
                    except:
                        raise # TODO better error handling
            except ValueError:
                pass

        # get the geocoder
        if self.google_api_key:
            geocoder = geopy.geocoders.Google(self.google_api_key)
        else:
            geocoder = geopy.geocoders.Google()
        locations = list(geocoder.geocode(location, exactly_one=False))
        if len(locations) == 1:
            return locations[0]
        else:
            if len(locations) > 1:

                # XXX work around Google geocoder bug where multiple
                # near identical addresses are returned
                # TODO: check to ensure they are close together
                if len(set([i[0] for i in locations])) == 1:
                    latlon = zip(*[i[1] for i in locations])
                    latlon = tuple([sum(latlon[i])/len(locations) for i in (0,1)])
                    
                    return locations[0][0], latlon

            raise GeolocationException(location, locations)

    def locate_ticket(self, ticket):
        if ticket.id:
            results = get_all_dict(self.env, "select latitude, longitude from ticket_location where ticket='%s'" % ticket.id)
            if results:
                return ticket['location'], (results[0]['latitude'], results[0]['longitude'])

        if ticket['location'] is None or not ticket['location'].strip():
            raise GeolocationException

        # XXX blindly assume UTF-8
        try:
            location = ticket['location'].encode('utf-8')
        except UnicodeEncodeError:
            raise

        location, (lat, lon) = self.geolocate(location)
        if ticket.id:
            self.set_location(ticket.id, lat, lon)
        return location, (lat, lon)

    def locate_tickets(self, tickets, req=None):
        locations = []
        for ticket in tickets:
            if isinstance(ticket, basestring):
                try:
                    ticket = int(ticket)
                except ValueError:
                    continue
            if isinstance(ticket, int):
                ticket = Ticket(self.env, ticket)
            try:
                address, (lat, lon) = self.locate_ticket(ticket)
                location = {'latitude': lat, 'longitude': lon, }
                if req:
                    location['content'] = self.feature_content(req, ticket)
                    # style for the markers
                    style = {}
                    for extension in self.marker_style:
                        style.update(extension.style(ticket, req, **style))
                    style = style or None
                    location['style'] = style

                locations.append(location)
            except GeolocationException:
                pass
        return locations

    def tickets_with_location(self):
        """return ids of all located tickets"""
        return set(get_column(self.env, 'ticket_location', 'ticket'))

    def set_location(self, ticket, lat, lon):
        """
        sets the ticket location in the db
        * ticket: the ticket id (int)
        * lat, lon: the lattitude and longtitude (degrees)
        """

        # determine if we need to insert or update the table
        # (SQL is retarded)
        if get_first_row(self.env, "select ticket from ticket_location where ticket='%s'" % ticket):
            execute_non_query(self.env, "update ticket_location set ticket=%s, latitude=%s, longitude=%s where ticket=%s", ticket, lat, lon, ticket)
        else:
            execute_non_query(self.env, "insert into ticket_location (ticket, latitude, longitude) values (%s, %s, %s)", ticket, lat, lon)
        
    def delete_location(self, ticket):
        """
        deletes a ticket location in the db
        * ticket: the ticket id (int)
        """
        
        if get_first_row(self.env, "select ticket from ticket_location where ticket='%s'" % ticket):
            execute_non_query(self.env, "delete from ticket_location where ticket='%s'" % ticket)


    def feature_content(self, req, ticket):
        """
        returns content of a feature popup window
        """
        if self.feature_popup:
            chrome = Chrome(self.env)
            _data = dict(req=req, 
                         ticket=ticket)
            template = chrome.load_template(self.feature_popup)
            return template.generate(**_data).render()
        else:
            return '<a href="%s">%s</a>' % (req.href('ticket', ticket.id), ticket['summary'])
