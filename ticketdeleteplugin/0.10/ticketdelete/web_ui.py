# Ticket deleting plugins

from trac import __version__ as TRAC_VERSION
from trac.core import *
from trac.ticket.model import Ticket
from trac.web.api import IRequestFilter
from trac.web.chrome import ITemplateProvider, add_script, add_stylesheet
from trac.util import sorted 

from webadmin.web_ui import IAdminPageProvider
import re
import traceback
import pprint
from time import strftime, localtime

__all__ = ['TicketDeletePlugin']

class TicketDeletePlugin(Component):
    """A small ticket deletion plugin."""
    
    implements(ITemplateProvider, IAdminPageProvider, IRequestFilter)

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, content_type):
        if template == 'ticket.cs' and req.perm.has_permission('TICKET_ADMIN'):
            add_script(req, 'ticketdelete/jquery.js')
            add_script(req, 'ticketdelete/ticketdelete.js')
            add_stylesheet(req, 'ticketdelete/ticketdelete.css')
        return template, content_type
 
    # IAdminPageProvider methods
    def get_admin_pages(self, req):
        if req.perm.has_permission('TICKET_ADMIN'):
            yield ('ticket', 'Ticket System', 'delete', 'Delete')
            yield ('ticket', 'Ticket System', 'comments', 'Delete Changes')
            
    def process_admin_request(self, req, cat, page, path_info):
        assert req.perm.has_permission('TICKET_ADMIN')
        
        req.hdf['ticketdelete.href'] = self.env.href('admin', cat, page)
        req.hdf['ticketdelete.page'] = page
        req.hdf['ticketdelete.redir'] = 1

        if req.method == 'POST':
            if page == 'delete':
                if 'ticketid' in req.args and 'ticketid2' in req.args:
                    if req.args.get('ticketid') == req.args.get('ticketid2'):
                        t = self._validate(req, req.args.get('ticketid'))
                        if t:
                            self._delete_ticket(t.id)
                            req.hdf['ticketdelete.message'] = "Ticket #%s has been deleted." % t.id
                            
                    else:
                        req.hdf['ticketdelete.message'] = "The two IDs did not match. Please try again."
            elif page == 'comments':
                if 'ticketid' in req.args:
                    req.redirect(self.env.href.admin(cat, page, req.args.get('ticketid')))
                else:
                    t = self._validate(req, path_info)
                    if t:
                        req.hdf['ticketdelete.href'] = self.env.href('admin', cat, page, path_info)
                        try:
                            deletions = None
                            if "multidelete" in req.args:
                                deletions = [x.split('_') for x in req.args.getlist('mdelete')]
                                deletions.sort(lambda a,b: cmp(b[1],a[1]))
                            else:
                                buttons = [x[6:] for x in req.args.keys() if x.startswith('delete')]
                                deletions = [buttons[0].split('_')]
                            if deletions:
                                for field, ts in deletions:
                                    #field, ts = button.split('_')
                                    ts = int(ts)
                                    self.log.debug('TicketDelete: Deleting change to ticket %s at %s (%s)'%(t.id,ts,field))
                                    self._delete_change(t.id, ts, field)
                                    req.hdf['ticketdelete.message'] = "Change to ticket #%s at %s has been modified" % (t.id, strftime('%a, %d %b %Y %H:%M:%S',localtime(ts)))
                                    req.hdf['ticketdelete.redir'] = 0
                        except ValueError, e:
                            self.log.debug("TicketDelete: Error is %s"%e)
                            self.log.debug("TicketDelete: args = '%s'"%req.args.items())
                            req.hdf['ticketdelete.message'] = "Timestamp '%s' not valid" % req.args.get('ts')                    
                    
                
        if path_info:
            t = self._validate(req, path_info)
            if t:
                if page == 'comments':
                    try:
                        selected = int(req.args.get('cnum')) - 1
                    except (TypeError, ValueError):
                        selected = None

                    ticket_data = {}
                    for time, author, field, oldvalue, newvalue, perm in t.get_changelog():
                        data = ticket_data.setdefault(str(time), {})
                        data.setdefault('fields', {})[field] = {'old': oldvalue, 'new': newvalue}
                        data['author'] = author
                        data['prettytime'] = strftime('%a, %d %b %Y %H:%M:%S',localtime(time))
                    
                    # Remove all attachment changes                    
                    for k, v in ticket_data.items():
                        if 'attachment' in v.get('fields', {}):
                            del ticket_data[k]
                            
                    # Check the boxes next to change number `selected`
                    time_list = list(sorted(ticket_data.iterkeys()))
                    if selected is not None and selected < len(time_list):
                        ticket_data[time_list[selected]]['checked'] = True
                    for time in time_list:
                        req.hdf['ticketdelete.changes.'+time] = ticket_data[time]
                elif page == 'delete':
                    req.hdf['ticketdelete.id'] = t.id
 
        return 'ticketdelete_admin.cs', None

    # ITemplateProvider methods
    def get_templates_dirs(self):
        """
        Return the absolute path of the directory containing the provided
        ClearSilver templates.
        """
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        """
        Return a list of directories with static resources (such as style
        sheets, images, etc.)

        Each item in the list must be a `(prefix, abspath)` tuple. The
        `prefix` part defines the path in the URL that requests to these
        resources are prefixed with.
        
        The `abspath` is the absolute path to the directory containing the
        resources on the local file system.
        """
        from pkg_resources import resource_filename
        return [('ticketdelete', resource_filename(__name__, 'htdocs'))]

    # Internal methods
    def _get_trac_version(self):
        md = re.match('(\d+)\.(\d+)',TRAC_VERSION)
        if md:
            return (int(md.group(1)),int(md.group(2)))
        else:
            return (0,0)

    def _validate(self, req, arg):
        """Validate that arg is a string containing a valid ticket ID."""
        try:
            id = int(arg)
            t = Ticket(self.env, id)
            return t
        except TracError:
            req.hdf['ticketdelete.message'] = "Ticket #%s not found. Please try again." % id
        except ValueError:
            req.hdf['ticketdelete.message'] = "Ticket ID '%s' is not valid. Please try again." % arg
        return False
                                                                                                                
    
    def _delete_ticket(self, id):
        """Delete the given ticket ID."""
        major, minor = self._get_trac_version()
        if major > 0 or minor >= 10:
            ticket = Ticket(self.env,id)
            ticket.delete()
        else:
            db = self.env.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("DELETE FROM ticket WHERE id=%s", (id,))
            cursor.execute("DELETE FROM ticket_change WHERE ticket=%s", (id,))
            cursor.execute("DELETE FROM attachment WHERE type='ticket' and id=%s", (id,))
            cursor.execute("DELETE FROM ticket_custom WHERE ticket=%s", (id,))
            db.commit()
            
    def _delete_change(self, id, ts, field=None):
        """Delete the change on the given ticket at the given timestamp."""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        ticket = Ticket(self.env,id)
        if field:
            if field == 'attachment':
                pass # Better handling still pending
            else:
                custom_fields = [f['name'] for f in ticket.fields if f.get('custom')]
                if field != "comment" and not [1 for time, author, field2, oldval, newval, _ in ticket.get_changelog() if time > ts and field == field2]:
                    oldval = [old for _, _, field2, old, _, _ in ticket.get_changelog(ts) if field2 == field][0]
                    if field in custom_fields:
                        cursor.execute("UPDATE ticket_custom SET value=%s WHERE ticket=%s AND name=%s", (oldval, id, field))
                    else:
                        cursor.execute("UPDATE ticket SET %s=%%s WHERE id=%%s" % field, (oldval, id))
                cursor.execute("DELETE FROM ticket_change WHERE ticket = %s AND time = %s AND field = %s", (id, ts, field))
        else:
            for _, _, field, _, _, _ in ticket.get_changelog(ts):
                self._delete_change(id, ts, field)
            
        db.commit()
