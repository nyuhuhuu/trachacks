# -*- coding: iso8859-1 -*-
#
# Copyright (C) 2003-2005 Edgewall Software
# Copyright (C) 2003-2005 Jonas Borgstr�m <jonas@edgewall.com>
# Copyright (C) 2006 Brad Anderson <brad@dsource.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.com/license.html.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://projects.edgewall.com/trac/.
#
# Author: Brad Anderson <brad@dsource.org>

import re
import time
import sha

from dbauth.env import *

from trac.core import *
from trac.web.api import IAuthenticator, IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider
from trac.util import escape, hex_entropy, TracError, Markup


class DbAuthLoginModule(Component):
    """Implements user authentication based on database tables and an HTML form,
    combined with cookies for communicating the login information across the whole site.
    """

    implements(IAuthenticator, INavigationContributor, ITemplateProvider, 
               IRequestHandler)

    def __init__(self):
        self.envname = get_envname(self.env)
        self.users = {                         # should we have defaults here?
           "table":self.env.config.get('dbauth', 'users_table'),
           "envname": self.env.config.get('dbauth','users_envname_field'),
           "username": self.env.config.get('dbauth','users_username_field'),
           "password": self.env.config.get('dbauth','users_password_field'),
           "email": self.env.config.get('dbauth','users_email_field')}
        self.cookies = {                         # should we have defaults here?
           "table":self.env.config.get('dbauth', 'cookies_table'),
           "envname": self.env.config.get('dbauth','cookies_envname_field'),
           "cookie": self.env.config.get('dbauth','cookies_cookie_field'),
           "username": self.env.config.get('dbauth','cookies_username_field'),
           "ipnr": self.env.config.get('dbauth','cookies_ipnr_field'),
           "unixtime": self.env.config.get('dbauth','cookies_unixtime_field')}


    # IAuthenticator methods

    def authenticate(self, req):
        authname = None
        if req.remote_user:
            authname = req.remote_user
        elif req.incookie.has_key('trac_db_auth'):
            authname = self._get_name_for_cookie(req, req.incookie['trac_db_auth'])

        if not authname:
            return None

        if self.config.getbool('trac', 'ignore_auth_case'):
            authname = authname.lower()

        return authname

    # INavigationContributor methods

    def get_active_navigation_item(self, req):
        return 'login'

    def get_navigation_items(self, req):
        if req.authname and req.authname != 'anonymous':
            yield 'metanav', 'login', Markup('logged in as <b>%s</b>' \
                    % req.authname)
            yield 'metanav', 'password', Markup('<a href="%s">Password</a>' \
                  % escape(self.env.href.password()))
            yield 'metanav', 'logout', Markup('<a href="%s">Logout</a>' \
                  % escape(self.env.href.logout()))
        else:
            yield 'metanav', 'login', Markup('<a href="%s">Login</a>' \
                  % escape(self.env.href.login()))

    # IRequestHandler methods

    def match_request(self, req):
        return re.match('/(login|password|logout)/?', req.path_info)

    def process_request(self, req):
        if req.method == 'POST':
            if req.args.get('login'):
                uid, pwd = req.args.get('uid'), req.args.get('pwd')
                if self._check_login(uid, pwd):
                    self._do_login(req)
                    req.redirect(req.href())
                else:
                    req.hdf["auth.message"] = "Login Incorrect"
            elif req.args.get('password'):
                old, new, repeat = req.args.get('opwd'), req.args.get('npwd'), req.args.get('rpwd')
                if not new or len(new) < 5:
                    req.hdf['auth.message'] = 'New password too short'
                elif new != repeat:
                    req.hdf['auth.message'] = 'Repeated password does not match'
                elif not self._check_login(req.authname, old):
                    req.hdf['auth.message'] = 'Wrong Password'
                else:
                    req.hdf['auth.message'] = 'Password Changed'
                    self._change_password(req, new)

        if req.path_info.startswith('/login'):
            # self._do_login(req)
            template = "login.cs"
        elif req.path_info.startswith('/password'):
            template = 'password.cs'
        elif req.path_info.startswith('/logout'):
            self._do_logout(req)
            req.redirect(self.env.href.login())
        return template, None

    # ITemplateProvider methods
    
    def get_htdocs_dirs(self):
        """Return the absolute path of a directory containing additional
        static resources (such as images, style sheets, etc).
        """
        from pkg_resources import resource_filename
        return [('dbauth', resource_filename(__name__, 'htdocs'))]
    
    def get_templates_dirs(self):
        """Return the absolute path of the directory containing the provided
        ClearSilver templates.
        """
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    # Internal methods

    def _check_login(self, uid, pwd):
        db = get_db(self.env)
        cursor = db.cursor()
        sql = "SELECT %s " \
               "FROM %s " \
               "WHERE %s = %%s" \
               "  AND (%s = %%s OR %s = 'all')" % \
               (self.users['password'], self.users['table'],
                self.users['username'], self.users['envname'],
                self.users['envname'])
        cursor.execute(sql, (uid, self.envname))
        hash = 'SHA-1:' + sha.new(pwd).hexdigest()
        if pwd.startswith('SHA-1:'):
            pwd = hash
        for row in cursor:
            if row[0] == pwd or row[0] == hash:
                return True

        return False

    def _do_login(self, req):
        """Log the remote user in."""

        remote_user = req.args.get('uid')
        remote_user = remote_user.lower()

        cookie = hex_entropy()
        db = get_db(self.env)
        cursor = db.cursor()
        sql = "INSERT INTO %s " \
              "(%s, %s, %s, %s, %s) " \
              "VALUES (%%s, %%s, %%s, %%s, %%s)" % \
              (self.cookies['table'], self.cookies['envname'], 
               self.cookies['cookie'], self.cookies['username'], 
               self.cookies['ipnr'], self.cookies['unixtime'])
        cursor.execute(sql, (self.envname, cookie, remote_user, 
                        req.remote_addr, int(time.time())))
        db.commit()

        req.authname = remote_user
        req.outcookie['trac_db_auth'] = cookie
        req.outcookie['trac_db_auth']['expires'] = 100000000
        req.outcookie['trac_db_auth']['path'] = self.env.href()

    def _do_logout(self, req):
        """Log the user out.

        Simply deletes the corresponding record from the auth_cookie table.
        """
        if req.authname == 'anonymous':
            # Not logged in
            return

        db = get_db(self.env)
        cursor = db.cursor()
        sql = "DELETE FROM %s " \
              "WHERE %s=%%s " \
              "  AND %s=%%s" % \
              (self.cookies['table'], self.cookies['username'],
               self.cookies['envname'])
        cursor.execute(sql, (req.authname, self.envname))
        db.commit()
        self._expire_cookie(req)

    def _expire_cookie(self, req):
        """Instruct the user agent to drop the auth cookie by setting the
        "expires" property to a date in the past.
        """
        req.outcookie['trac_db_auth'] = ''
        req.outcookie['trac_db_auth']['path'] = self.env.href()
        req.outcookie['trac_db_auth']['expires'] = -10000

    def _get_name_for_cookie(self, req, cookie):
        db = get_db(self.env)
        cursor = db.cursor()
        sql = "SELECT %s " \
               "FROM %s " \
               "WHERE %s = %%s " \
               "  AND %s = %%s" % \
               (self.cookies['username'], self.cookies['table'],
                self.cookies['cookie'], self.cookies['envname'])
        cursor.execute(sql, (cookie.value,self.envname))
        row = cursor.fetchone()
        if not row:
            # The cookie is invalid (or has been purged from the database), so
            # tell the user agent to drop it as it is invalid
            self._expire_cookie(req)
            return None

        return row[0]

    def _change_password(self, req, newpwd):
        if req.authname == 'anonymous':
            # Not logged in
            return

        # check which environment to use
        db = get_db(self.env)
        cursor = db.cursor()
        envname = 'all'
        sql = "SELECT %s " \
               "FROM %s " \
               "WHERE %s = %%s" \
               "  AND %s = %%s" % \
               (self.users['username'], self.users['table'],
                self.users['username'], self.users['envname'])
        cursor.execute(sql, (req.authname, self.envname))
        if cursor.fetchone():
            envname = self.envname

        # change the password
        newpwd = 'SHA-1:' + sha.new(newpwd).hexdigest()
        sql = "UPDATE %s " \
               "SET %s = %%s " \
               "WHERE %s = %%s " \
               "  AND %s = %%s" % \
               (self.users['table'], self.users['password'],
                self.users['username'], self.users['envname'])
        print(sql)
        print(sql % (newpwd, req.authname, envname))
        cursor.execute(sql, (newpwd, req.authname, envname))
        db.commit()

    def _redirect_back(self, req):
        """Redirect the user back to the URL she came from."""
        referer = req.get_header('Referer')
        if referer and not referer.startswith(req.base_url):
            # only redirect to referer if the latter is from the same
            # instance
            referer = None
        req.redirect(referer or self.env.abs_href())
