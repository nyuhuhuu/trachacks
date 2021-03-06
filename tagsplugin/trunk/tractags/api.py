# -*- coding: utf-8 -*-
#
# Copyright (C) 2006 Alec Thomas <alec@swapoff.org>
# Copyright (C) 2011,2012 Steffen Hoffmann <hoff.st@web.de>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import re

from genshi import Markup
from pkg_resources import resource_filename

from trac.config import BoolOption
from trac.core import Component, ExtensionPoint, Interface, TracError, \
                      implements
from trac.perm import IPermissionRequestor, PermissionError
from trac.resource import IResourceManager, get_resource_url, \
                          get_resource_description
from trac.util.text import to_unicode
from trac.wiki.model import WikiPage

# Import translation functions.
# Fallbacks make Babel still optional and provide for Trac 0.11.
try:
    from trac.util.translation  import domain_functions
    add_domain, _, N_, gettext, ngettext, tag_ = \
        domain_functions('tractags', ('add_domain', '_', 'N_', 'gettext',
                                      'ngettext', 'tag_'))
    dgettext = None
except ImportError:
    from genshi.builder  import tag as tag_
    from trac.util.translation  import gettext
    _ = gettext
    N_ = lambda text: text
    def add_domain(a,b,c=None):
        pass
    def dgettext(domain, string, **kwargs):
        return safefmt(string, kwargs)
    def ngettext(singular, plural, num, **kwargs):
        string = num == 1 and singular or plural
        kwargs.setdefault('num', num)
        return safefmt(string, kwargs)
    def safefmt(string, kwargs):
        if kwargs:
            try:
                return string % kwargs
            except KeyError:
                pass
        return string

from tractags.model import resource_tags, tag_resource, tagged_resources
# Now call module importing i18n methods from here.
from tractags.query import *


class InvalidTagRealm(TracError):
    pass


class ITagProvider(Interface):
    """The interface for Components providing per-realm tag storage and
    manipulation methods.

    Change comments and reparenting are supported since tags-0.7.
    """
    def get_taggable_realm():
        """Return the realm this provider supports tags on."""

    def get_tagged_resources(req, tags=None, filter=None):
        """Return a sequence of resources and *all* their tags.

        :param tags: If provided, return only those resources with the given
                     tags.
        :param filter: If provided, skip matching resources.

        :rtype: Sequence of (resource, tags) tuples.
        """

    def get_resource_tags(req, resource):
        """Get tags for a Resource object."""

    def set_resource_tags(req, resource, tags, comment=u''):
        """Set tags for a resource."""

    def reparent_resource_tags(req, old_resource, resource, comment=u''):
        """Move tags, typically when renaming an existing resource."""

    def remove_resource_tags(req, resource, comment=u''):
        """Remove all tags from a resource."""

    def describe_tagged_resource(req, resource):
        """Return a one line description of the tagged resource."""


class DefaultTagProvider(Component):
    """An abstract base tag provider that stores tags in the database.

    Use this if you need storage for your tags. Simply set the class variable
    `realm` and optionally `check_permission()`.

    See tractags.wiki.WikiTagProvider for an example.
    """

    implements(ITagProvider)

    abstract = True

    # Resource realm this provider manages tags for. Set this.
    realm = None

    # Public methods

    def check_permission(self, perm, action):
        """Delegate function for checking permissions.

        Override to implement custom permissions. Defaults to TAGS_VIEW and
        TAGS_MODIFY.
        """
        map = {'view': 'TAGS_VIEW', 'modify': 'TAGS_MODIFY'}
        return map[action] in perm('tag')

    # ITagProvider methods

    def get_taggable_realm(self):
        return self.realm

    def get_tagged_resources(self, req, tags, filter=None):
        if not self.check_permission(req.perm, 'view'):
            return
        return tagged_resources(self.env, self.check_permission, req.perm,
                                self.realm, tags, filter)

    def get_resource_tags(self, req, resource):
        assert resource.realm == self.realm
        if not self.check_permission(req.perm(resource), 'view'):
            return
        return resource_tags(self.env, self.realm, resource.id)

    def set_resource_tags(self, req, resource, tags, comment=u''):
        assert resource.realm == self.realm
        if not self.check_permission(req.perm(resource), 'modify'):
            raise PermissionError(resource=resource, env=self.env)
        tag_resource(self.env, self.realm, to_unicode(resource.id), tags=tags)

    def reparent_resource_tags(self, req, old_resource, resource,
                               comment=u''):
        assert old_resource.realm == self.realm
        assert resource.realm == self.realm
        if not self.check_permission(req.perm(old_resource), 'modify'):
            raise PermissionError(resource=old_resource, env=self.env)
        if not self.check_permission(req.perm(resource), 'modify'):
            raise PermissionError(resource=resource, env=self.env)
        tag_resource(self.env, self.realm, to_unicode(old_resource.id),
                     to_unicode(resource.id))

    def remove_resource_tags(self, req, resource, comment=u''):
        assert resource.realm == self.realm
        if not self.check_permission(req.perm(resource), 'modify'):
            raise PermissionError(resource=resource, env=self.env)
        tag_resource(self.env, self.realm, to_unicode(resource.id))

    def describe_tagged_resource(self, req, resource):
        return ''


class TagSystem(Component):
    """Tagging system for Trac."""

    implements(IPermissionRequestor, IResourceManager)

    tag_providers = ExtensionPoint(ITagProvider)

    wiki_page_link = BoolOption('tags', 'wiki_page_link', True,
        doc="Link a tag to the wiki page with same name, if it exists.")

    # Internal variables
    _realm = re.compile('realm:(\w+)', re.U | re.I)
    _tag_split = re.compile('[,\s]+')
    _realm_provider_map = None

    def __init__(self):
        # Bind the 'tractags' catalog to the specified locale directory.
        locale_dir = resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)

    # Public methods

    def query(self, req, query='', attribute_handlers=None):
        """Return a sequence of (resource, tags) tuples matching a query.

        Query syntax is described in tractags.query.

        :param attribute_handlers: Register additional query attribute
                                   handlers. See Query documentation for more
                                   information.
        """
        def realm_handler(_, node, context):
            return query.match(node, [context.realm])

        all_attribute_handlers = {
            'realm': realm_handler,
        }
        all_attribute_handlers.update(attribute_handlers or {})
        query = Query(query, attribute_handlers=all_attribute_handlers)
        providers = set()
        for m in self._realm.finditer(query.as_string()):
            realm = m.group(1)
            providers.add(self._get_provider(realm))
        if not providers:
            providers = self.tag_providers

        query_tags = set(query.terms())
        for provider in providers:
            self.env.log.debug('Querying ' + repr(provider))
            for resource, tags in provider.get_tagged_resources(req,
                                                          query_tags) or []:
                if query(tags, context=resource):
                    yield resource, tags

    def get_all_tags(self, req, query=''):
        """Return all tags, optionally only on resources matching query.

        Returns a dictionary with tag name as key and tag frequency as value.
        """
        all_tags = {}
        for resource, tags in self.query(req, query):
            for tag in tags:
                if tag in all_tags:
                    all_tags[tag] += 1
                else:
                    all_tags[tag] = 1
        return all_tags

    def get_tags(self, req, resource):
        """Get tags for resource."""
        return set(self._get_provider(resource.realm) \
                   .get_resource_tags(req, resource))

    def set_tags(self, req, resource, tags, comment=u''):
        """Set tags on a resource.

        Existing tags are replaced.
        """
        try:
            return self._get_provider(resource.realm) \
                   .set_resource_tags(req, resource, set(tags), comment)
        except TypeError:
            # Handle old style tag providers gracefully.
            return self._get_provider(resource.realm) \
                   .set_resource_tags(req, resource, set(tags))

    def add_tags(self, req, resource, tags, comment=u''):
        """Add to existing tags on a resource."""
        tags = set(tags)
        tags.update(self.get_tags(req, resource))
        try:
            self.set_tags(req, resource, tags, comment)
        except TypeError:
            # Handle old style tag providers gracefully.
            self.set_tags(req, resource, tags)

    def reparent_tags(self, req, old_resource, resource, comment=u''):
        """Move tags, typically when renaming an existing resource.

        Tags can't be moved between different tag realms with intention.
        """
        provider = self._get_provider(old_resource.realm)
        provider.reparent_resource_tags(req, old_resource, resource, comment)

    def replace_tag(self, req, old_tags, new_tag=None, comment=u'',
                    allow_delete=False):
        """Replace one or more tags in all resources it exists/they exist in.

        Tag deletion is optionally allowed for convenience as well.
        """
        # Provide list regardless of attribute type.
        for resource_provider in self.tag_providers:
            for resource, tags in \
                    resource_provider.get_tagged_resources(req, old_tags):
                old_tags = set(old_tags)
                if old_tags.issuperset(tags) and not new_tag:
                    if allow_delete:
                        self.delete_tags(req, resource, None, comment)
                else:
                    s_tags = set(tags)
                    eff_tags = s_tag - old_tags
                    if new_tag:
                        eff_tags.add(new_tag)
                    # Prevent to touch resources without effective change.
                    if eff_tags != s_tags and (allow_delete or new_tag):
                        self.set_tags(req, resource, eff_tags, comment)

    def delete_tags(self, req, resource, tags=None, comment=u''):
        """Delete tags on a resource.

        If tags is None, remove all tags on the resource.
        """
        provider = self._get_provider(resource.realm)
        if tags is None:
            try:
                provider.remove_resource_tags(req, resource, comment)
            except TypeError:
                 # Handle old style tag providers gracefully.
                provider.remove_resource_tags(req, resource)
        else:
            current_tags = set(provider.get_resource_tags(req, resource))
            current_tags.difference_update(tags)
            try:
                provider.set_resource_tags(req, resource, current_tags,
                                           comment)
            except TypeError:
                 # Handle old style tag providers gracefully.
                provider.set_resource_tags(req, resource, current_tags)

    def split_into_tags(self, text):
        """Split plain text into tags."""
        return set([tag.strip() for tag in self._tag_split.split(text)
                   if tag.strip()])

    def describe_tagged_resource(self, req, resource):
        """Return a short description of a taggable resource."""
        provider = self._get_provider(resource.realm)
        if hasattr(provider, 'describe_tagged_resource'):
            return provider.describe_tagged_resource(req, resource)
        else:
            self.env.log.warning('ITagProvider %r does not implement '
                                 'describe_tagged_resource()' % provider)
            return ''
    
    # IPermissionRequestor method
    def get_permission_actions(self):
        action = ['TAGS_VIEW', 'TAGS_MODIFY']
        actions = [action[0], (action[1], [action[0]]),
                   ('TAGS_ADMIN', action)]
        return actions

    # IResourceManager methods

    def get_resource_realms(self):
        yield 'tag'

    def get_resource_url(self, resource, href, form_realms=None, **kwargs):
        if self.wiki_page_link:
            page = WikiPage(self.env, resource.id)
            if page.exists:
                return get_resource_url(self.env, page.resource, href,
                                        **kwargs)
        return href.tags(unicode(resource.id), form_realms, **kwargs)

    def get_resource_description(self, resource, format='default',
                                 context=None, **kwargs):
        if self.wiki_page_link:
            page = WikiPage(self.env, resource.id)
            if page.exists:
                return get_resource_description(self.env, page.resource,
                                                format, **kwargs)
        rid = to_unicode(resource.id)
        if format in ('compact', 'default'):
            return rid
        else:
            return u'tag:%s' % rid

    # Internal methods

    def _populate_provider_map(self):
        if self._realm_provider_map is None:
            self._realm_provider_map = {}
            for provider in self.tag_providers:
                self._realm_provider_map[provider.get_taggable_realm()] = \
                    provider

    def _get_provider(self, realm):
        self._populate_provider_map()
        try:
            return self._realm_provider_map[realm]
        except KeyError:
            raise InvalidTagRealm(_("Tags are not supported on the '%s' realm")
                                  % realm)
