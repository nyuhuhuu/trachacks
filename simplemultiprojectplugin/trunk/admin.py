# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Christopher Paredes
#

# Trac core imports
from trac.core import *
from trac.config import *

# Trac extension point imports
from trac.admin.api import IAdminPanelProvider
from trac.web.chrome import ITemplateProvider, add_notice

# Model Class
from simplemultiproject.model import *

# Trac Administration Panel
class SmpAdminPanel(Component):
    """Modifies Trac UI for editing Projects"""

    implements(IAdminPanelProvider, ITemplateProvider)
    def __init__(self):
        self.__SmpModel = SmpModel(self.env)

    def add_project(self, name, description):
        try:
            self.log.info("Simple Multi Project: Adding project %s" % (name))
            self.__SmpModel.insert_project(name, description)
            return True

        except Exception, e:
            self.log.error("Add Project Error: %s" % (e, ))
            return False

    def update_project(self, id, name, description):
        try:
            self.log.info("Simple Multi Project: Modify project %s" % (name))
            self.__SmpModel.update_project(id, name, description)
            return True
        
        except Exception, e:
            self.log.error("Modify Project Error: %s" % (e, ))
            return False

    def render_admin_panel(self, req, category, page, path_info):
        """Return the template and data used to render our administration page."""
        projects_rows  = self.__SmpModel.get_all_projects()
        projects = []
        for row in projects_rows:
            projects.append({'id': row[0], 'name':row[1], 'description': row[2]})

        if path_info:
            if req.method == 'POST':
                if req.args.get('modify'):
                    if not self.update_project(req.args.get('id'), req.args.get('name'), req.args.get('description')):
                        self.log.error("SimpleMultiProject Error: Failed to added project '%s'" % (req.args.get('name'),))
                    else:
                        add_notice(req, "'The project '%s' has been modify." % req.args.get('name'))
                        req.redirect(req.href.admin(category, page))
                elif req.args.get('cancel'):
                    req.redirect(req.href.admin(category, page))
                else:
                    pass
            else:
                for project in projects:
                    if project['id'] == int(path_info):
                        data = {'view': 'detail', 'project': project}
        else:
            if req.method == 'POST':
                if req.args.get('add'):
                    if req.args.get('name') != '':
                        if not self.add_project(req.args.get('name'), req.args.get('description')):
                            self.log.error("SimpleMultiProject Error: Failed to added project '%s'" % (req.args.get('name'),))
                        else:
                            add_notice(req, "'The project '%s' has been added." % req.args.get('name'))
                            req.redirect(req.href.admin(category, page))
                         
                    else:
                        raise TracError('No name input')

                elif req.args.get('remove'):
                    sel = req.args.get('sel')
                    if not sel:
                        raise TracError('No project selected')
                    if not isinstance(sel, list):
                        sel = [sel]

                    self.__SmpModel.delete_project(sel)

                    req.redirect(req.href.admin(category, page))

                else:
                    pass
            else:
                data = {'view':'init', 'projects':projects, }

        return 'simplemultiproject_adminpanel.html', data

    def get_htdocs_dirs(self):
        return []

    def get_admin_panels(self, req):
        return (('projects', 'Manage Projects', 'simplemultiproject', 'Projects'),)

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]