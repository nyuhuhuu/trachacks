import re
from pkg_resources import resource_filename

from trac.core import *
from trac.web.api import IRequestFilter, IRequestHandler
from trac.web.chrome import ITemplateProvider, add_script, add_stylesheet
from trac.config import ListOption
from trac.prefs.api import IPreferencePanelProvider
from trac.util.translation import domain_functions

from dynfields.options import Options
from dynfields.rules import add_domain, _, IRule


class DynamicFieldsModule(Component):
    """A module that dynamically alters ticket fields based an extensible
    set of rules.  Uses jQuery for full implementation."""
    
    implements(IRequestFilter, IRequestHandler, ITemplateProvider,
               IPreferencePanelProvider)

    rules = ExtensionPoint(IRule)
    
    def __init__(self):
    # bind the 'dynfields' catalog to the specified locale directory
        locale_dir = resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        return [('dynfields', resource_filename(__name__, 'htdocs'))]
    
    def get_templates_dirs(self):
        return [resource_filename(__name__, 'templates')]

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler
    
    def post_process_request(self, req, template, data, content_type):
        if ((req.path_info.startswith('/ticket') or
            req.path_info.startswith('/newticket')) and \
                req.perm.has_permission('TICKET_MODIFY') \
            ) or ( \
            req.path_info.startswith('/query') and \
                req.perm.has_permission('REPORT_VIEW')):
            add_script(req, 'dynfields/dynfields.js')
            add_script(req, 'dynfields/layout.js')
            add_script(req, 'dynfields/rules.js')
        return template, data, content_type
    
    # IRequestHandler methods
    def match_request(self, req):
        return req.path_info.startswith('/dynfields')
    
    def process_request(self, req):
        data = {'triggers':self._get_triggers(req)}
        return 'dynfields.html', {'data': data},'text/javascript' 
    
    def _get_triggers(self, req):
        """Converts trac.ini config to dict of triggers with rule specs."""
        triggers = {}
        opts = Options(self.env)
        for key in opts:
            # extract the target field
            target_re = re.compile(r"(?P<target>[^.]+).*")
            target = target_re.match(key).groupdict()['target']
            
            # extract rule specifications from configs
            for rule in self.rules:
                trigger = rule.get_trigger(target, key, opts)
                if not trigger:
                    continue
                if not opts.is_enabled(req, key):
                    continue
                value,_ = opts.get_value_and_options(req, target, key)
                spec = {'rule_name':rule.name, 'trigger':trigger,
                        'target':target, 'value':value}
                rule.update_spec(req, key, opts, spec)
                if trigger not in triggers:
                    triggers[trigger] = [] # rule specs
                triggers[trigger].append(spec)
            
        return triggers

    # IPreferencePanelProvider methods
    def get_preference_panels(self, req):
        if self._get_prefs_data(req): # only show if there are preferences
            # TRANSLATOR: the preferences tab label
            yield 'dynfields', _("Dynamic Fields")

    def render_preference_panel(self, req, panel):
        opts = Options(self.env)
        if req.method == 'POST':
            opts.set_prefs(req)
        data = self._get_prefs_data(req, opts)
        return 'prefs_panel.html', {'data':data, 'saved':req.method == 'POST'}
    
    def _get_prefs_data(self, req, opts=None):
        """Returns the pref data, a dict of rule class titles whose values
        include lists of rule spec preference dicts each with these keys:
        
          id (based on unique key)
          label (of checkbox)
          enabled ('1' or '0')
          type ('none' or 'select'; TODO: 'text') 
          options (list of options if type is 'select')
          value (saved preference or default value)
        """
        if opts is None:
            opts = Options(self.env)
        data = {}
        for rule in self.rules:
            for key in opts:
                if not opts.has_pref(key):
                   continue
                target_re = re.compile(r"(?P<target>[^.]+).*")
                target = target_re.match(key).groupdict()['target']
                trigger = rule.get_trigger(target, key, opts)
                if not trigger:
                    continue
                
                # this rule spec has a pref - so get it!
                pref = opts.get_pref(req, target, key)
                rule.update_pref(req, trigger, target, key, opts, pref)
                if rule.title not in data:
                    data[rule.title] = {'desc':rule.desc, 'prefs':[]}
                data[rule.title]['prefs'].append(pref)
        return data
