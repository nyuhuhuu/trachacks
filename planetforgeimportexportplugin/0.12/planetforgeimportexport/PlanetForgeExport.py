# -*- coding: utf-8 -*-

from trac.core import *

from trac.util.html import html
from trac.util.text import print_table, printout
from trac.util.translation import _, N_, gettext

from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider, Chrome

from trac.db.api import with_transaction

from trac.admin.api import IAdminCommandProvider, IAdminPanelProvider

from trac.loader import get_plugin_info

from trac.ticket import model
from trac.ticket.model import Ticket

from urlparse import urlparse
import os
import json
import tempfile
from zipfile import ZipFile
from datetime import date, datetime


class PlanetForgeExport(Component):
    implements(IAdminCommandProvider, IAdminPanelProvider, ITemplateProvider)


    # CLI part (trac-admin /path/to/trac planetforge [export|report] ...)

    def get_admin_commands(self):
        yield ('planetforge report', '', 'Report exportable items (size, quantity)', None, self.cli_report) # safe a component is a singleton
        yield ('planetforge export', '', 'Export all Trac items in "PlanetForge" format', None, self.cli_export)

    # make a report on what can be exported from command line
    def cli_report(self) :
        infos_dic = self._getTracVolume()
        infos = [ (n, infos_dic[n]) for n in infos_dic ]
        infos.sort
        print_table(infos, (_('type'), _('volume')))


    # export all trac items from commande line
    def cli_export(self) :
        print "Not implemented yet."


    # WEB part (/admin/planetforge/export)

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]


    def get_htdocs_dirs(self):
        return []

    def get_admin_panels(self, req):
        if 'TRAC_ADMIN' in req.perm:
            yield ('planetforge', 'PlanetForge', 'export', 'Export')

    def render_admin_panel(self, req, category, page, path_info):
        req.perm.require('TRAC_ADMIN')
        res = {'action' : 'report'}
        action = req.args.get('action', '')
        if action == 'export' :
            ticket = req.args.get('ticket', '').strip() == 'on'
            wiki = req.args.get('wiki', '').strip() == 'on' 
            revision = req.args.get('revision', '').strip() == 'on' 
            ticket_change = req.args.get('ticket_change', '').strip() == 'on'
            res = self.web_export(req)
        else : # action == 'report'
            res = self.web_report(req)
        return './export.html', res

    def web_report(self, req) :
        count   = self._get_item_count()
        checked = {}
        checked['wiki']       = { 'checked': 'checked' }
        checked['ticket']     = { 'checked': 'checked' }
        checked['attachment'] = { 'checked': 'checked' }
        checked['session']    = { 'checked': 'checked' }
        checked['component']  = { 'checked': 'checked' }
        checked['milestone']  = { 'checked': 'checked' }
        checked['permission'] = { 'checked': 'checked' }
        checked['debug']      = { }
        return {'count': count , 'checked': checked , 'action': 'report'}

    def web_export(self, req) :
        todo = {}
        for i in [ 'wiki', 'ticket', 'attachment', 'session', 'component', 'milestone', 'permission', 'debug' ] :
            todo[i] = req.args.get(i, '').strip() == 'on'
        meta = self._do_export(todo)
        dump = json.dumps(meta, sort_keys=True, indent=2)

        if todo['debug']:
            return {'action': 'debug', 'dump': dump}

        tmpname = tempfile.mktemp()
        out = ZipFile(tmpname, 'w') 
        out.writestr('mimetype', 'application/x-planetforge-forge-export-coclicoformat')
        out.writestr('Plucker/JSON_Pluck.txt', dump)
        if todo['attachment']:
            self._do_export_files(out)
        out.close()
        req.send_header('Content-disposition', 'attachment; filename=%s-export-%s.zip' % (
            self.config.get('project', 'name'),
            date.today().strftime('%Y-%m-%d') ))
        req.send_file(tmpname, 'application/x-planetforge-forge-export-coclicoformat')
        os.remove(tmpname)
        return {}
    
    def _get_item_count(self) :
        res = {}
        @with_transaction(self.env)
        def getInfo(db) :
            cursor = db.cursor()

            cursor.execute("SELECT count(*) FROM ticket")
            res['ticket'] = cursor.fetchall()[0]

            cursor.execute("SELECT count(*) FROM ticket_change")
            res['ticket_change'] = cursor.fetchall()[0]

            cursor.execute("SELECT count(distinct name) FROM wiki")
            res['wiki'] = cursor.fetchall()[0]

            cursor.execute("SELECT count(*), (sum(size)+1023)/1024 FROM attachment")
            [ res['attachment'], res['attachment_size'] ] = cursor.fetchall()[0]

            cursor.execute("SELECT count(*) FROM component")
            res['component'] = cursor.fetchall()[0]

            cursor.execute("SELECT count(*) FROM milestone")
            res['milestone'] = cursor.fetchall()[0]

            cursor.execute("SELECT count(*) FROM permission")
            res['permission'] = cursor.fetchall()[0]

            cursor.execute("SELECT count(distinct(sid)) FROM session WHERE authenticated=1")
            res['session'] = cursor.fetchall()[0]
        return res


    """ TODO / notes

    * docman, frs, news ?
    * scm, scm_type: Trac 0.12 has multiple repositories per project
    * forgeversion: missing
    * users.role should be users.roles = [ ... ]
    * roles: check with http://trac.edgewall.org/wiki/TracPermissions (~40)


    """
    def _do_export(self, todo):
        self.base_url = self.config.get('trac', 'base_url')
        meta = {
            'rdf:about': self.base_url,
            'rdf:type' : 'http://planetforge.org/ns/forgeplucker_dump/project_dump#',
            'prefixes': {
                'dcterms'      : 'http://purl.org/dc/terms/',
                'doap'         : 'http://usefulinc.com/ns/doap#',
                'foaf'         : 'http://xmlns.com/foaf/0.1/',
                'forgeplucker' : 'http://planetforge.org/ns/forgeplucker_dump/',
                'oslc'         : 'http://open-services.net/ns/core#',
                'oslc_cm'      : 'http://open-services.net/ns/cm#',
                'planetforge'  : 'http://coclico-project.org/ontology/planetforge#',
                'rdf'          : 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'sioc'         : 'http://rdfs.org/sioc/ns#'
            },
            'forgeplucker:project'   : self._do_export_project(),
            'forgeplucker:tools'     : self._do_export_tools(),
        }
        if todo['ticket']:
            meta['forgepluckers:trackers'] = self._do_export_trackers()
        if todo['permission']:
            meta['forgeplucker:roles'] = self._do_export_roles()
        if todo['session']:
            meta['forgeplucker:users'] = self._do_export_users()
        if todo['wiki']:
            meta['forgeplucker:wiki'] = self._do_export_wiki()
        if todo['attachment']:
            meta['forgeplucker:files'] = self._do_export_files_meta()
        #if todo['milestone']:
        #if todo['component']:
        return meta

    def _do_export_project(self):
        return {
            'URL'            : self.base_url,
            'class'          : 'PROJET',
            'description'    : self.config.get('project', 'descr'), 
            'forgetype'      : 'Trac',
            'format_version' : 1,
            'homepage'       : self.config.get('project', 'url'),
            'host'           : urlparse(self.base_url).netloc,
            'project'        : self.config.get('project', 'name'),
            'registered'     : '?',
            'scm'            : self.base_url + "/browser",
            'scm_type'       : 'svn',
            'trackers_list'  : [ self.base_url + '/report' ],
        }

    def _do_export_tools(self):
        plugins = get_plugin_info(self.env, include_core=True)
        t = {}
        for p in plugins :
            for (m_name, m) in p['modules'].iteritems() :
                for (c_name, c) in m['components'].iteritems() :
                    t[self.base_url + "/#" + c['full_name']] = {
                        'name' : c['full_name'],
                        'type' : 'UnknownTool'
                    }
        return t

    def _do_export_roles(self):
        return {
            'BROWSER_VIEW' : 'View directory listings in the repository browser',
            'LOG_VIEW' : 'View revision logs of files and directories in the repository browser',
            'FILE_VIEW' : 'View files in the repository browser',
            'CHANGESET_VIEW' : 'View repository check-ins',
            
            'TICKET_VIEW' : 'View existing tickets and perform ticket queries',
            'TICKET_CREATE' : 'Create new tickets',
            'TICKET_APPEND' : 'Add comments or attachments to tickets',
            'TICKET_CHGPROP' : 'Modify ticket properties (priority, assignment, keywords, etc.) with the following exceptions: edit description field, add/remove other users from cc field when logged in, and set email to pref',
            'TICKET_MODIFY' : 'Includes both TICKET_APPEND and TICKET_CHGPROP, and in addition allows resolving tickets. Tickets can be assigned to users through a drop-down list when the list of possible owners has been restricted.',
            'TICKET_EDIT_CC' : 'Full modify cc field',
            'TICKET_EDIT_DESCRIPTION' : 'Modify description field',
            'TICKET_EDIT_COMMENT' : 'Modify comments',
            'TICKET_ADMIN' : 'All TICKET_* permissions, plus the deletion of ticket attachments and modification of the reporter and description fields. It also allows managing ticket properties in the WebAdmin panel.',
            
            'MILESTONE_VIEW' : 'View milestones and assign tickets to milestones.',
            'MILESTONE_CREATE' : 'Create a new milestone',
            'MILESTONE_MODIFY' : 'Modify existing milestones',
            'MILESTONE_DELETE' : 'Delete milestones',
            'MILESTONE_ADMIN' : 'All MILESTONE_* permissions',
            'ROADMAP_VIEW' : 'View the roadmap page, is not (yet) the same as MILESTONE_VIEW, see #4292',
            'ROADMAP_ADMIN' : 'to be removed with #3022, replaced by MILESTONE_ADMIN',
            
            'REPORT_VIEW' : 'View reports, i.e. the "view tickets" link.',
            'REPORT_SQL_VIEW' : 'View the underlying SQL query of a report',
            'REPORT_CREATE' : 'Create new reports',
            'REPORT_MODIFY' : 'Modify existing reports',
            'REPORT_DELETE' : 'Delete reports',
            'REPORT_ADMIN' : 'All REPORT_* permissions',
            
            'WIKI_VIEW' : 'View existing wiki pages',
            'WIKI_CREATE' : 'Create new wiki pages',
            'WIKI_MODIFY' : 'Change wiki pages',
            'WIKI_RENAME' : 'Rename wiki pages',
            'WIKI_DELETE' : 'Delete wiki pages and attachments',
            'WIKI_ADMIN' : 'All WIKI_* permissions, plus the management of readonly pages.',
            
            'PERMISSION_GRANT' : 'add/grant a permission',
            'PERMISSION_REVOKE' : 'remove/revoke a permission',
            'PERMISSION_ADMIN' : 'All PERMISSION_* permissions',
            
            'TIMELINE_VIEW' : 'View the timeline page',
            'SEARCH_VIEW' : 'View and execute search queries',
            'CONFIG_VIEW' : 'Enables additional pages on About Trac that show the current configuration or the list of installed plugins',
            'EMAIL_VIEW' : 'Shows email addresses even if trac show_email_addresses configuration option is false'
        }

    def _do_export_trackers(self):
        ticket_ids = []
        @with_transaction(self.env)
        def get_tickets(db) :
            cursor = db.cursor()
            cursor.execute("SELECT id FROM ticket");
            for t in cursor:
                ticket_ids.append(t[0]);
        a = []
        for id in ticket_ids:
            a.append(self._do_export_ticket(id))

        v = {
            'Component'  : [x.name for x in model.Component.select(self.env)],
            'Milestone'  : [x.name for x in model.Milestone.select(self.env)],
            'Priority'   : [x.name for x in model.Priority.select(self.env)],
            'Resolution' : [x.name for x in model.Resolution.select(self.env)],
            'Severity'   : [x.name for x in model.Severity.select(self.env)],
            'Type'       : [x.name for x in model.Type.select(self.env)],
            'Version'    : [x.name for x in model.Version.select(self.env)]
        }
        return {
            'artifacts'  : a,
            'label'      : 'Trac tickets',
            'type'       : 'generic',
            'url'        : self.base_url + '/report',
            'vocabulary' : v
        }

    def _do_export_ticket(self, id):
        ticket = Ticket(self.env, id)
        t = {
            'class'       : 'ARTIFACT',
            'id'          : id,
            'URL'         : self.base_url + '/ticket/%d' % id,
            'submitter'   : ticket.values.get('reporter', 'None'),
            'assigned_to' : ticket.values.get('owner', 'None'),
            'comments'    : [], #TODO
            'history'     : [], #TODO
            'attachments' : [], #TODO
        }
        for val in [ 'Component', 'Severity', 'Priority', 'Version', 'Milestone', 'Status', 'Resolution', 'Description', 'Summary' ] :
            t[val] = ticket.values.get(val.lower(), 'None')
        return t

    def _do_export_users(self):
        # First pass: gather uniques sid's
        sid = []
        @with_transaction(self.env)
        def get_sid(db) :
            cursor = db.cursor()
            cursor.execute("SELECT DISTINCT sid FROM session WHERE authenticated=1");
            for s in cursor :
                sid.append(s[0])

        # Second pass: fetch sid attributes for all sid's
        u = {}
        for s in sid :
            attr = { 'email': '', 'name': '' }
            @with_transaction(self.env)
            def get_sid_attr(db) :
                cursor = db.cursor()
                cursor.execute("SELECT name,value FROM session_attribute WHERE sid=%s", (s,));
                for r in cursor :
                    attr[r[0]] = r[1]
            u[s] = {
                'URL'       : self.base_url + '/prefs',
                'mail'      : attr['email'],
                'real_name' : attr['name'],
                'role'      : '?'
            }
        return u

    def _do_export_wiki(self):
        wiki = {}
        @with_transaction(self.env)
        def getInfo(db) :
            cursor = db.cursor()
            cursor.execute("SELECT name,version,time,author,text,comment FROM wiki ORDER BY name,version")

            curpage = []
            curname = ''
            for page in cursor:
                if curname == '':
                    curname = page[0]
                if curname != page[0]:
                    wiki[curname] = curpage
                    curpage = []
                    curname = page[0]
                curpage.append({
                    'version': page[1],
                    'date':    datetime.utcfromtimestamp(page[2] / 10**6).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'author':  page[3],
                    'text':    page[4],
                    'comment': page[5] or '',
                })
            wiki[curname] = curpage
        return wiki

    def _do_export_files_meta(self):
        files = []
        @with_transaction(self.env)
        def getInfo(db) :
            cursor = db.cursor()
            cursor.execute("SELECT type,id,filename,size,time,description,author FROM attachment")

            for att in cursor:
                files.append({
                    'filename'    : att[2],
                    'filepath'    : '%s/%s/%s' % (att[0], att[1], att[2]),
                    'relation'    : '%s#%s' % (att[0], att[1]),
                    'size'        : att[3],
                    'date'        : datetime.utcfromtimestamp(att[4] / 10**6).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'description' : att[5],
                    'author'      : att[6],
                })
        return files

    def _do_export_files(self, out):
        @with_transaction(self.env)
        def getInfo(db) :
            cursor = db.cursor()
            cursor.execute("SELECT type,id,filename FROM attachment")

            for att in cursor:
                src = os.path.join(self.env.path, 'attachments', att[0], att[1], att[2])
                arcname = '%s/%s/%s' % (att[0], att[1], att[2])
                out.write(src, arcname)

