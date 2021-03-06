#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Copyright (C) 2008 General de Software de Canarias.
 
 Author: Carlos López Pérez <carlos.lopezperez@gmail.com>
"""

import ldap

from trac.core import implements, Component
from trac.web.api import IRequestFilter, IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.env import Environment
from trac.util import escape, Markup

class AccountLDAP(Component):
    """Gestiona el api para la interacción con el LDAP y la gestión del trac
    """
    implements(IRequestFilter, INavigationContributor, IRequestHandler, ITemplateProvider)
    
    MODULE_NAME = 'accountldap'    
    
    def __init__(self):
        """Se realiza la conexión con el LDAP.
        """
        self.enabled = self.config.getbool('ldap', 'enable')
        if not self.enabled:
            return
        self.basedn = self.config.get('ldap', 'basedn')
        self.userdn = self.config.get('ldap', 'user_rdn')
        try:
            self.ldap = ldap.open(self.config.get('ldap', 'host'))
            self.ldap.simple_bind(self.config.get('ldap', 'bind_user'),  self.config.get('ldap', 'bind_passwd'))
        except ldap.LDAPError, e:
            self.log.error('Connection LDAP problems. Check trac.ini ldap options')
            self.enabled = false
    #
    #------------------------------------------------------------------------- ITemplateProvider interface
    #
    def get_templates_dirs(self):
        """Return a list of directories containing the provided ClearSilver
            templates.
        """
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
    #
    #--------------------------------------------------------------------------- IRequestHandler interface
    #
    def match_request(self, req):
        return req.path_info == '/' + self.MODULE_NAME

    def process_request(self, req):
        template = self.MODULE_NAME + '.cs'
        if req.method != 'POST':
            return template, None
        
        p1 = req.args.get('password1')
        p2 = req.args.get('password2')
        old = req.args.get('oldpassword')
        if p1 != p2:
            req.hdf['accountldap.message'] = Markup('<center style="color: chocolate">%s<b>%s</b></center>' % (u'Password mismatch',  u' please use exactly the same password'))
            return template, None
        if old == p1:
            req.hdf['accountldap.message'] = Markup('<center style="color: chocolate">%s<b>%s</b></center>' % (u'Password is not changed',  u' please change your password'))
            return template, None
        #dn = 'uid=%s,%s,%s' % (req.authname, self.userdn, self.basedn)
        try:
            base = self.userdn + ',' + self.basedn
            ld_results = self.ldap.search_s(base, ldap.SCOPE_SUBTREE, 'uid=%s' % req.authname, ['dn'])
            # FIXME: Use only the first found DN. We should only have single DN here
            if ld_results :
                dn = ld_results[0][0]
                self.ldap.passwd_s(dn, old, p1)
            else :
                raise LDAPError('Failed to find user in LDAP')
        except ldap.LDAPError, e:
            req.hdf['accountldap.message'] = Markup('<center style="color: chocolate">%s<b>%s</b></center>' % (u'Failed to change your password',  u' An error occurred during LDAP pasword operation. Please consult your log file.'))
            self.log.warn('Ldap change password. %s' % e)
            return template, None
        req.hdf['accountldap.message'] = Markup('<center style="color: green"><b>%s</b></center>' %  u'Password successfully changed')             
        return template, None
    #
    #------------------------------------------------------------------------------- IRequestFilter interface
    #
    def pre_process_request(self, req, handler):
        return handler
            
    def post_process_request(self, req, template, content_type):
        if not req.remote_user or req.session.has_key('email'):
            return template, None 
        uid = req.remote_user.lower()
        self.log.error('uid %s session %s' % (uid, req.session))
        name, email = self._getUserAttributes(uid)
        req.session['name'] = name        
        req.session['email'] = email
        return template, None
    #
    #----------------------------------------------------------------- INavigationContributor interface
    #
    def get_active_navigation_item(self, req):
        return self.MODULE_NAME
                
    def get_navigation_items(self, req):
#        if not req.authname or not req.session.has_key('email') :
#            return
#        uid = req.remote_user.lower()
#       XXX: it seems that password changing should be OK even without email
        if not req.authname :
            return
        if req.authname == 'anonymous' :
            return
        yield 'metanav', self.MODULE_NAME,  Markup('<a href="%s">%s</a>' % (self.env.href.accountldap(), u'Password'))
    #
    # ----------------------------------------------------------------------------------------- helper methods
    #
    def _getUserAttributes(self, uid):
        """Devuelve el nombre completo y el correo definido en el ldap
        """
        filter = 'uid=%s' % uid
        result = []
        try:
            id = self.ldap.search(self.basedn, ldap.SCOPE_SUBTREE, filter, None)
            type, data = self.ldap.result(id, 0)
        except ldap.LDAPError, e:
            self.log.error('Search LDAP problems. Check trac.ini ldap options')
            return ('', '')
        self.log.info('%s - %s' % (data[0][1]['cn'][0], data[0][1]['mail'][0]))
        return (data[0][1]['cn'][0], data[0][1]['mail'][0])
