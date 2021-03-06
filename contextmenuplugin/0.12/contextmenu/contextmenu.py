# -*- coding: utf-8 -*-
#
# Copyright (c) 2010, Logica
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

from genshi.builder import tag
from genshi.core import Markup
from genshi.filters.transform import Transformer
from trac.config import Option
from trac.core import Component, ExtensionPoint, implements
from trac.util.translation import _
from trac.web.api import ITemplateStreamFilter
from trac.web.chrome import ITemplateProvider, add_script, add_stylesheet

from api import ISourceBrowserContextMenuProvider

import os


class SourceBrowserContextMenu(Component):
    """Component for adding a context menu to each item in the Trac browser
    file-list
    """
    implements(ITemplateStreamFilter, ITemplateProvider)
    
    context_menu_providers = ExtensionPoint(ISourceBrowserContextMenuProvider)
    
    # ITemplateStreamFilter methods
    
    def filter_stream(self, req, method, filename, stream, data):
        if filename in ('browser.html', 'dir_entries.html'):
            if 'path' not in data:
                # Probably an upstream error
                return stream
            # provide a link to the svn repository at the top of the Browse Source listing
            if self.env.is_component_enabled('contextmenu.contextmenu.SubversionLink'):
                content = SubversionLink(self.env).get_content(req, data['path'], stream, data)
                if content:
                    stream |= Transformer('//div[@id="content"]/h1').after(content)
            # No dir entries; we're showing a file
            if not data['dir']:
                return stream
            # FIXME: The idx is only good for finding rows, not generating element ids.
            # Xhr rows are only using dir_entries.html, not browser.html.
            # The xhr-added rows' ids are added using js (see expand_dir.js)
            add_stylesheet(req, 'contextmenu/contextmenu.css')
            add_script(req, 'contextmenu/contextmenu.js')
            if 'up' in data['chrome']['links']:
                # Start appending stuff on 2nd tbody row when we have a parent dir link
                row_index = 2
                # Remove colspan and insert an empty cell for checkbox column
                stream |= Transformer('//table[@id="dirlist"]//td[@colspan="5"]').attr('colspan', None).before(tag.td())
            else:
                # First row = //tr[1]
                row_index = 1

            for idx, entry in enumerate(data['dir']['entries']):
                menu = tag.div(tag.span(Markup('&#9662;'), style='color: #bbb'),
                               tag.div(class_='ctx-foldable', style='display:none'),
                               id='ctx%s' % idx, class_='context-menu')
                for provider in sorted(self.context_menu_providers, key=lambda x: x.get_order(req)):
                    content = provider.get_content(req, entry, stream, data)
                    if content:
                        menu.children[1].append(tag.div(content))
                ## XHR rows don't have a tbody in the stream
                if data['xhr']:
                    path_prefix = ''
                else:
                    path_prefix = '//table[@id="dirlist"]//tbody'
                # Add the menu
                stream |= Transformer('%s//tr[%d]//td[@class="name"]' % (path_prefix, idx + row_index)).prepend(menu)
                if provider.get_draw_separator(req):
                    menu.children[1].append(tag.div(class_='separator'))
                # Add td+checkbox
                cb = tag.td(tag.input(type='checkbox', id="cb%s" % idx, class_='fileselect'))
                stream |= Transformer('%s//tr[%d]//td[@class="name"]' % (path_prefix, idx + row_index)).before(cb)

            stream |= Transformer('//th[1]').before(tag.th())

        return stream

    # ITemplateProvider methods
    
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('contextmenu', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []


class InternalNameHolder(Component):
    """This component holds a reference to the file on this row
    for the javascript to use"""
    implements(ISourceBrowserContextMenuProvider)
    # IContextMenuProvider methods
    def get_order(self, req):
        return 0

    def get_draw_separator(self, req):
        return False
    
    def get_content(self, req, entry, stream, data):
        reponame = data['reponame'] or ''
        filename = os.path.normpath(os.path.join(reponame, entry.path))
        return tag.span(filename, class_='filenameholder %s' % entry.kind,
                        style='display:none')


class SubversionLink(Component):
    """Generate direct link to file in svn repo"""
    implements(ISourceBrowserContextMenuProvider)

    # IContextMenuProvider methods
    def get_order(self, req):
        return 1

    def get_draw_separator(self, req):
        return True
    
    def get_content(self, req, entry, stream, data):
        if self.env.is_component_enabled('svnurls.svnurls.svnurls'):
            # Another plugin provides links to subversion, so we won't duplicate them.
            return None
        repos, path, rev = get_repository_path_and_rev(entry, data)
        if repos:
            href = repos.get_path_url(path, rev)
            if href:
                return tag.a(_("Subversion"), href=href)

        # Probably repositories not configured or
        # no URL has been specified for the repository
        return None


class WikiToBrowserLink(Component):
    """Generate wiki link"""
    implements(ISourceBrowserContextMenuProvider)

    # IContextMenuProvider methods
    def get_order(self, req):
        return 2

    def get_draw_separator(self, req):
        return True

    def get_content(self, req, entry, stream, data):
        repos, path, rev = get_repository_path_and_rev(entry, data)
        href = ''
        if repos.name:
            href += '/' + repos.name
        href = 'source:/%s' % path
        if rev:
            href += '@%s' % data['rev']
        return tag.a(_("Wiki Link (to copy)"), href=href)


class SendResourceLink(Component):
    """Generate "Share file" menu item"""
    implements(ISourceBrowserContextMenuProvider)

    def get_order(self, req):
        return 10

    def get_draw_separator(self, req):
        return False

    # IContextMenuProvider methods
    def get_content(self, req, entry, stream, data):
        if not entry.isdir:
            return tag.a(_("Share file"), href=req.href.share(entry.path) + '/FIXME')


def get_repository_path_and_rev(entry, data):
    rev = None
    if isinstance(entry, basestring):
        path = entry
        if 'rev' in data and data['rev']:
            rev = data['rev']
    else:
        try:
            path = entry.path
            rev = entry.rev
        except AttributeError:
            path = entry['path']
            rev = entry['rev']

    return data['repos'], path, rev

