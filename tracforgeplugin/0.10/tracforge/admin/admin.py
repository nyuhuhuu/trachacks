from trac.core import *

from webadmin.web_ui import IAdminPageProvider

from model import Project, Prototype

class TracForgeAdminModule(Component):
    """A module to manage projects in TracForge."""

    implements(IAdminPageProvider)    
    
    # IAdminPageProvider methods
    def get_admin_pages(self, req):
        if req.perm.has_permission('TRACFORGE_ADMIN'):
            yield ('tracforge', 'TracForge', 'admin', 'Project Admin')
            
    def process_admin_request(self, req, cat, page, path_info):
        projects = [Project(self.env, n) for n in Project.select(self.env)]

        if req.method == 'POST':
            if 'create' in req.args.keys(): # Project creation
                name = req.args.get('shortname', '').strip()
                fullname = req.args.get('fullname', '').strip()
                env_path = req.args.get('env_path', '').strip()
                proto_name = req.args.get('prototype', '').strip()
                if not (name and fullname and env_path and proto_name):
                    raise TracError('All arguments are required')
                
                # Make the models
                proj = Project(self.env, name)
                proto = Prototype(self.env, proto_name)
                if not proto.exists:
                    raise TracError('Penguins on fire')
                
                # Store the project
                proj.env_path = env_path
                proj.save()
                
                # Apply the prototype
                output = proto.apply(req, proj)
                
                req.hdf['tracforge.output'] = output
                req.hdf['tracforge.href.projects'] = req.href.admin(cat, page)
                #req.args['hdfdump'] = 1
                return 'admin_tracforge_project_new.cs', None
                req.redirect(req.href.admin(cat, page))
            elif 'delete' in req.args.keys(): # Project deleteion
                raise TracError, 'Not implemented yet. Sorry.'
    
        project_data = {}
        for proj in projects:
            project_data[proj.name] = {
                'fullname': proj.valid and proj.env.project_name or '',
                'env_path': proj.env_path,
            }
            
        req.hdf['tracforge.projects'] = project_data
        req.hdf['tracforge.prototypes'] = Prototype.select(self.env)
    
        return 'admin_tracforge.cs', None
             
