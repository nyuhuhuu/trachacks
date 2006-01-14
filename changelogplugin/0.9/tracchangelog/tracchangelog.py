# tracchangelog plugin

from trac.core import *
from trac.util import escape, Markup
from trac.wiki.api import IWikiMacroProvider
from trac.wiki.formatter import wiki_to_html
from trac.util import format_datetime
from StringIO import StringIO

class TracChangeLogPlugin(Component):
    """ Provides the [[ChangLog(path[, limit[, rev]])]] macro, which dumps the change log
        for path of revision rev, back limit revisions. "rev" can be 0 for the latest
        revision. """

    implements(IWikiMacroProvider)

    def get_macros(self):
        yield 'ChangeLog'

    def get_macro_description(self, name):
        return pydoc.getdoc(self)

    def render_macro(self, req, name, content):
        path, limit, rev = ([x.strip() for x in (content or '').split(',')] + [0, 9999])[0:3]

        repo = self.env.get_repository(req.authname)

        rev = repo.normalize_rev(int(rev) or repo.get_youngest_rev())
        path = repo.normalize_path(path)
        limit = int(limit)
        
        node = repo.get_node(path, rev)
        out = StringIO()
        for npath, nrev, nlog in node.get_history(limit):
            change = repo.get_changeset(nrev)
            out.write(wiki_to_html("'''%s by %s'''\n\n%s" % (format_datetime(change.date), change.author, change.message), self.env, req));
        return out.getvalue()
