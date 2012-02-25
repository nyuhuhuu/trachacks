# vim: expandtab
import re, time
from StringIO import StringIO

from genshi.builder import tag

from trac.core import *
from trac.wiki.formatter import format_to_html
from trac.util import TracError
from trac.util.text import to_unicode
from trac.web.chrome import add_stylesheet, add_javascript, ITemplateProvider
from trac.wiki.api import parse_args, IWikiMacroProvider
from trac.wiki.macros import WikiMacroBase
from trac.wiki.model import WikiPage
from trac.wiki.web_ui import WikiModule

class SpoilerMacro(WikiMacroBase):
    """A macro to add spoilers to a page. Usage:
    """
    implements(IWikiMacroProvider, ITemplateProvider)

    def expand_macro(self, formatter, name, content, args):
        self.log.debug("SpoilerMacro: expand_macro")
        add_stylesheet(formatter.req, 'spoiler/css/spoiler.css')
        add_javascript(formatter.req, 'spoiler/js/spoiler.js')
        output = tag.div(class_="spoiler")
        input = tag.input(type_="button", onclick_="showSpoiler(this);", value="Spoiler!")
        text = tag.div(class_="spoilerinner", style_="display:none;")
        text.append(content)
        output.append(input)
        output.append(text)
        self.log.debug("SpoilerMacro: expand_macro output")
        return output
    
    ## ITemplateProvider
            
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename                             
        return [('spoiler', resource_filename(__name__, 'htdocs'))]   
                                      
    def get_templates_dirs(self):
        return []