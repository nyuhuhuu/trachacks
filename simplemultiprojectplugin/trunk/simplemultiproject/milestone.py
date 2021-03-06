from genshi.builder import tag
from genshi.filters.transform import Transformer
from simplemultiproject.model import *
from trac.core import *
from trac.web.api import IRequestFilter
from trac.web.api import ITemplateStreamFilter
from trac.wiki.formatter import wiki_to_oneliner
from operator import itemgetter
import re

class SmpMilestoneProject(Component):
    """Add a 'Project' attribute to milestones.
    """
    implements(IRequestFilter, ITemplateStreamFilter)

    # Init
    def __init__(self):
        self.__SmpModel = SmpModel(self.env)


    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        action = req.args.get('action', 'view')

        if req.path_info.startswith('/milestone'):
            if req.method == 'POST':
                milestone = req.args.get('name')
                milestone_id = req.args.get('id')
                id_project = req.args.get('project')

                if action == 'edit':
                    if milestone_id != milestone:
                        self.__SmpModel.rename_milestone_project(milestone_id, milestone)
                        
                    id_project_milestone = self.__SmpModel.get_id_project_milestone(milestone)
                    
                    if id_project:
                        if id_project_milestone == None:
                            self.__SmpModel.insert_milestone_project(milestone, id_project)
                        else:
                            if id_project_milestone[0] != id_project:
                                self.__SmpModel.update_milestone_project(milestone, id_project)
                    else:
                        self.__SmpModel.delete_milestone_project(milestone)

                elif action == 'new':
                    if id_project:
                        self.__SmpModel.insert_milestone_project(milestone, id_project)
                            
                elif action == 'delete':
                    self.__SmpModel.delete_milestone_project(milestone_id)
        elif req.path_info.startswith('/admin/ticket/milestones'):
            if req.method == 'POST':
                milestones = req.args.get('sel')
                remove = req.args.get('remove')
                save = req.args.get('save')
                if not remove is None and not milestones is None:
                    if type(milestones) is list:
                        for ms in milestones:
                            self.__SmpModel.delete_milestone_project(ms)
                    else:
                        self.__SmpModel.delete_milestone_project(milestones) 
                elif not save is None:
                    match = re.match(r'/admin/ticket/milestones/(.+)$', req.path_info)
                    if match and match.group(1) != req.args.get('name'):                    
                        self.__SmpModel.rename_milestone_project(match.group(1), req.args.get('name'))

        return handler
        
    def post_process_request(self, req, template, data, content_type):
        return template, data, content_type

    # ITemplateStreamFilter methods

    def filter_stream(self, req, method, filename, stream, data):
        action = req.args.get('action', 'view')

        # Allow setting project for milestone
        if filename == 'milestone_edit.html':
            if action == 'new':
                filter = Transformer('//form[@id="edit"]/div[1]')
                return stream | filter.before(self.__new_project())
            elif action == 'edit':
                filter = Transformer('//form[@id="edit"]/div[1]')
                return stream | filter.before(self.__edit_project(data))
        # Display project for milestone
        elif filename == 'milestone_view.html':
            milestone = data.get('milestone').name
            filter = Transformer('//div[@class="info"]/p[@class="date"]')
            return stream | filter.before(self.__project_display(req, milestone))
        return stream

    # internal methods

    def __project_display(self, req, milestone):
        row = self.__SmpModel.get_project_milestone(milestone)
        
        if row:
            return tag.span(
                            tag.h3(wiki_to_oneliner("Project: %s" % (row[0],), self.env, req=req))
                            )
        else:
            return []
    
    def __edit_project(self, data):
        milestone = data.get('milestone').name
        all_projects = self.__SmpModel.get_all_projects()
        id_project_milestone = self.__SmpModel.get_id_project_milestone(milestone)

        if id_project_milestone != None:
            id_project_selected = id_project_milestone[0]
        else:
            id_project_selected = None

        return tag.div(
                       tag.label(
                       'Project:',
                       tag.br(),
                       tag.select(
                       tag.option(),
                       [tag.option(row[1], selected=(id_project_selected == row[0] or None), value=row[0]) for row in sorted(all_projects, key=itemgetter(1))],
                       name="project")
                       ),
                       class_="field")

    def __new_project(self):
        all_projects = self.__SmpModel.get_all_projects()

        return tag.div(
                       tag.label(
                       'Project:',
                       tag.br(),
                       tag.select(
                       tag.option(),
                       [tag.option(row[1], value=row[0]) for row in sorted(all_projects, key=itemgetter(1))],
                       name="project")
                       ),
                       class_="field")
