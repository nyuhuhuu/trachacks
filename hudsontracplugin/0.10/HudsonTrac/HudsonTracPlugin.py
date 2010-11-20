# -*- coding: utf-8 -*-
"""
A Trac plugin which interfaces with the Hudson Continuous integration server

You can configure this component via the
[wiki:TracIni#hudson-section "[hudson]"]
section in the trac.ini file.

See also:
 - http://hudson-ci.org/
 - http://wiki.hudson-ci.org/display/HUDSON/Trac+Plugin
"""

import time
import urllib2
import base64
from datetime import datetime
from trac.core import *
from trac.config import Option, BoolOption
from trac.perm import IPermissionRequestor
from trac.util import Markup, format_datetime, pretty_timedelta
from trac.util.text import unicode_quote
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.web.chrome import add_stylesheet
from trac.wiki.formatter import wiki_to_oneliner
try:
    from trac.timeline.api import ITimelineEventProvider
except ImportError:
    from trac.Timeline import ITimelineEventProvider
try:
    from ast import literal_eval
except ImportError:
    def literal_eval(str):
        return eval(str, {"__builtins__":None}, {"True":True, "False":False})

class HudsonTracPlugin(Component):
    """
    Display Hudson results in the timeline and an entry in the main navigation
    bar.
    """

    implements(INavigationContributor, ITimelineEventProvider,
               ITemplateProvider, IPermissionRequestor)

    disp_mod = BoolOption('hudson', 'display_modules', 'false',
                          'Display status of modules in the timeline too. ')
    job_url  = Option('hudson', 'job_url', 'http://localhost/hudson/',
                      'The url of the top-level hudson page if you want to '
                      'display all jobs, or a job or module url (such as '
                      'http://localhost/hudson/job/build_foo/) if you want '
                      'only display builds from a single job or module. '
                      'This must be an absolute url.')
    username = Option('hudson', 'username', '',
                      'The username to use to access hudson')
    password = Option('hudson', 'password', '',
                      'The password to use to access hudson')
    nav_url  = Option('hudson', 'main_page', '/hudson/',
                      'The url of the hudson main page to which the trac nav '
                      'entry should link; if empty, no entry is created in '
                      'the nav bar. This may be a relative url.')
    disp_tab = BoolOption('hudson', 'display_in_new_tab', 'false',
                          'Open hudson page in new tab/window')
    alt_succ = BoolOption('hudson', 'alternate_success_icon', 'false',
                          'Use an alternate success icon (green ball instead '
                          'of blue)')
    use_desc = BoolOption('hudson', 'display_build_descriptions', 'true',
                          'Whether to display the build descriptions for '
                          'each build instead of the canned "Build finished '
                          'successfully" etc messages.')
    disp_building = BoolOption('hudson', 'display_building', False,
                               'Also show in-progress builds')
    list_changesets = BoolOption('hudson', 'list_changesets', False,
                                 'List the changesets for each build')

    def __init__(self):
        # get base api url
        api_url = unicode_quote(self.job_url, '/%:@')
        if api_url and api_url[-1] != '/':
            api_url += '/'
        api_url += 'api/python'

        # set up http authentication
        pwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        pwd_mgr.add_password(None, api_url, self.username, self.password)

        b_auth = urllib2.HTTPBasicAuthHandler(pwd_mgr)
        d_auth = urllib2.HTTPDigestAuthHandler(pwd_mgr)

        self.url_opener = urllib2.build_opener(b_auth, d_auth,
                                            self.HudsonFormLoginHandler(self))

        self.env.log.debug("registered auth-handler for '%s', username='%s'",
                           api_url, self.username)

        # construct tree=... parameter to query for the desired items
        tree = '%(b)s'
        if self.disp_mod:
            tree += ',modules[%(b)s]'
        if '/job/' not in api_url:
            tree = 'jobs[' + tree + ']'

        items = 'builds[building,timestamp,duration,result,description,url,' \
                'fullDisplayName'
        if self.list_changesets:
            items += ',changeSet[items[revision,id]]'
        items += ']'

        # assemble final url
        tree = tree % {'b': items}
        self.info_url = '%s?tree=%s' % (api_url, tree)

        self.env.log.debug("Build-info url: '%s'", self.info_url)

    # IPermissionRequestor methods  

    def get_permission_actions(self):
        return ['BUILD_VIEW']

    # INavigationContributor methods

    def get_active_navigation_item(self, req):
        return 'builds'

    def get_navigation_items(self, req):
        if self.nav_url and req.perm.has_permission('BUILD_VIEW'):
            yield 'mainnav', 'builds', Markup('<a href="%s"%s>Builds</a>' % \
                    (self.nav_url, self.disp_tab and ' target="hudson"' or ''))

    # ITemplateProvider methods
    def get_templates_dirs(self):
        return []

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('HudsonTrac', resource_filename(__name__, 'htdocs'))]

    # ITimelineEventProvider methods

    def get_timeline_filters(self, req):
        if req.perm.has_permission('BUILD_VIEW'):
            yield ('build', 'Hudson Builds')

    def __fmt_changeset(self, rev, req):
        # use format_to_oneliner and drop num_args hack when we drop Trac 0.10
        # support
        import inspect
        num_args = len(inspect.getargspec(wiki_to_oneliner)[0])
        if num_args > 5:
            return wiki_to_oneliner('[%s]' % rev, self.env, req=req)
        else:
            return wiki_to_oneliner('[%s]' % rev, self.env)

    def get_timeline_events(self, req, start, stop, filters):
        if 'build' not in filters or not req.perm.has_permission('BUILD_VIEW'):
            return

        # helper to extract all values in a nested structure of lists and dicts
        def __find_all(d, paths):
            if not isinstance(paths, basestring):
                for path in paths:
                    for item in __find_all(d, path):
                        yield item
                return

            parts = paths.split('.', 1)
            key = parts[0]
            if key in d:
                if len(parts) > 1:
                    for item in __find_all(d[key], parts[1]):
                        yield item
                else:
                    yield d[key]
            elif not isinstance(d, dict) and not isinstance(d, basestring):
                for elem in d:
                    for item in __find_all(elem, paths):
                        yield item

        def __find_first(d, paths):
            l = list(__find_all(d, paths))
            return len(l) > 0 and l[0] or None

        # extract individual builds; what we may get from hudson is:
        # {'jobs': [{'modules': [{'builds': [{'building': False, ...
        # {'jobs': [{'builds': [{'building': False, ...
        # {'modules': [{'builds': [{'building': False, ...
        # {'builds': [{'building': False, ...
        def __get_builds(info):
            for arr in __find_all(info, ['builds', 'modules.builds',
                                         'jobs.builds','jobs.modules.builds']):
                for item in arr:
                    yield item

        # Support both Trac 0.10 and 0.11
        if isinstance(start, datetime): # Trac>=0.11
            from trac.util.datefmt import to_timestamp
            start = to_timestamp(start)
            stop = to_timestamp(stop)

        add_stylesheet(req, 'HudsonTrac/hudsontrac.css')

        # get and parse the build-info
        try:
            local_exc = False
            try:
                resp = self.url_opener.open(self.info_url)
                cset = resp.info().getparam('charset') or 'ISO-8859-1'

                ct   = resp.info().gettype()
                if ct != 'text/x-python':
                    local_exc = True
                    raise IOError(
                        "Error getting build info from '%s': returned document "
                        "has unexpected type '%s' (expected 'text/x-python'). "
                        "The returned text is:\n%s" %
                        (self.info_url, ct, unicode(resp.read(), cset)))

                info = literal_eval(resp.read())
            except Exception:
                if local_exc:
                    raise

                import sys
                self.env.log.exception("Error getting build info from '%s'",
                                       self.info_url)
                raise IOError(
                    "Error getting build info from '%s': %s: %s. This most "
                    "likely means you configured a wrong job_url, username, "
                    "or password." %
                    (self.info_url, sys.exc_info()[0].__name__,
                     str(sys.exc_info()[1])))
        finally:
            self.url_opener.close()

        # extract all build entries
        for entry in __get_builds(info):
            # get result, optionally ignoring builds that are still running
            if entry['building']:
                if self.disp_building:
                    result = 'IN-PROGRESS'
                else:
                    continue
            else:
                result = entry['result']

            # get start/stop times
            started = entry['timestamp'] / 1000
            if started < start or started > stop:
                continue

            if result == 'IN-PROGRESS':
                # we hope the clocks are close...
                completed = time.time()
            else:
                completed = (entry['timestamp'] + entry['duration']) / 1000

            # get message
            message, kind = {
                'SUCCESS': ('Build finished successfully',
                            ('build-successful',
                             'build-successful-alt')[self.alt_succ]),
                'UNSTABLE': ('Build unstable', 'build-unstable'),
                'ABORTED': ('Build aborted', 'build-aborted'),
                'IN-PROGRESS': ('Build in progress',
                                ('build-inprogress',
                                 'build-inprogress-alt')[self.alt_succ]),
                }.get(result, ('Build failed', 'build-failed'))

            if self.use_desc:
                message = entry['description'] and \
                            unicode(entry['description'], cset) or message

            # get changesets
            changesets = ''
            if self.list_changesets:
                paths = ['changeSet.items.revision', 'changeSet.items.id']
                revs = [unicode(str(r), cset) for r in __find_all(entry, paths)]
                if revs:
                    revs = [self.__fmt_changeset(r, req) for r in revs]
                    changesets = '<br/>Changesets: ' + ', '.join(revs)

            # format response
            if result == 'IN-PROGRESS':
                comment = Markup("%s since %s, duration %s%s" % (
                                 message, format_datetime(started),
                                 pretty_timedelta(started, completed),
                                 changesets))
            else:
                comment = Markup("%s at %s, duration %s%s" % (
                                 message, format_datetime(completed),
                                 pretty_timedelta(started, completed),
                                 changesets))

            href  = entry['url']
            title = 'Build "%s" (%s)' % \
                    (unicode(entry['fullDisplayName'], cset), result.lower())

            yield kind, href, title, completed, None, comment

    class HudsonFormLoginHandler(urllib2.BaseHandler):
        def __init__(self, parent):
            self.p = parent

        def http_error_403(self, req, fp, code, msg, headers):
            for h in self.p.url_opener.handlers:
                if isinstance(h, self.p.HTTPOpenHandlerBasicAuthNoChallenge):
                    return

            self.p.url_opener.add_handler(
                self.p.HTTPOpenHandlerBasicAuthNoChallenge(self.p.username,
                                                           self.p.password))
            self.p.env.log.debug(
                "registered auth-handler for form-based authentication")

            fp.close()
            return self.p.url_opener.open(req)

    class HTTPOpenHandlerBasicAuthNoChallenge(urllib2.BaseHandler):

        auth_header = 'Authorization'

        def __init__(self, username, password):
            raw = "%s:%s" % (username, password)
            self.auth = 'Basic %s' % base64.b64encode(raw).strip()

        def default_open(self, req):
            req.add_header(self.auth_header, self.auth)

