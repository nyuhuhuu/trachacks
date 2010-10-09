# -*- coding: utf-8 -*-
#
# Copyright (C) 2005,2006,2007 Matthew Good <trac@matt-good.net>
#
# "THE BEER-WARE LICENSE" (Revision 42):
# <trac@matt-good.net> wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return.   Matthew Good
#
# Author: Matthew Good <trac@matt-good.net>

import errno
import os.path
# DEVEL: Use `with` statement for better file access code,
#   taking care of Python 2.5, but not needed for Python >= 2.6
#from __future__ import with_statement

from trac.core import *
from trac.config import Option

from api import IPasswordStore
from pwhash import htpasswd, htdigest
from util import EnvRelativePathOption


class AbstractPasswordFileStore(Component):
    """Base class for managing password files.

    Derived classes support different formats such as
    Apache's htpasswd and htdigest format.
    See these concrete sub-classes for usage information.
    """

    filename = EnvRelativePathOption('account-manager', 'password_file')

    def has_user(self, user):
        return user in self.get_users()

    def get_users(self):
        filename = str(self.filename)
        if not os.path.exists(filename):
            self.log.debug('acct_mgr: get_users() -- '
                           'Can\'t locate "%s"' % filename)
            return []
        return self._get_users(filename)

    def set_password(self, user, password):
        user = user.encode('utf-8')
        password = password.encode('utf-8')
        return not self._update_file(self.prefix(user),
                                     self.userline(user, password))

    def delete_user(self, user):
        user = user.encode('utf-8')
        return self._update_file(self.prefix(user), None)

    def check_password(self, user, password):
        filename = str(self.filename)
        if not os.path.exists(filename):
            self.log.debug('acct_mgr: check_password() -- '
                           'Can\'t locate "%s"' % filename)
            return False
        user = user.encode('utf-8')
        password = password.encode('utf-8')
        prefix = self.prefix(user)
        try:
            f = open(filename, 'Ur')
            for line in f:
                if line.startswith(prefix):
                    return self._check_userline(user, password,
                            line[len(prefix):].rstrip('\n'))
        finally:
            f.close()
        return None

    def _update_file(self, prefix, userline):
        """Add or remove user and change password.

        If `userline` is empty, the line starting with `prefix` is removed
        from the user file. Otherwise the line starting with `prefix`
        is updated to `userline`.  If no line starts with `prefix`,
        the `userline` is appended to the file.

        Returns `True` if a line matching `prefix` was updated,
        `False` otherwise.
        """
        filename = str(self.filename)
        matched = False
        new_lines = []
        try:
            # Open existing file read-only to read old content.
            # DEVEL: Use `with` statement available in Python >= 2.5
            #   as soon as we don't need to support 2.4 anymore.
            eol = '\n'
            f = open(filename, 'Ur')
            lines = f.readlines()
            newlines = f.newlines
            if newlines is not None:
                if isinstance(newlines, str):
                    newlines = [f.newlines]
                elif isinstance(newlines, tuple):
                    newlines = list(f.newlines)
                if '\n' not in newlines:
                    if '\r\n' in newlines:
                        # Windows newline style
                        eol = '\r\n'
                    elif '\r' in newlines:
                        # MacOS newline style
                        eol = '\r'

            # DEVEL: Beware, in shared use there is a race-condition,
            #   since file changes by other programs that occure from now on
            #   are currently not detected and will get overwritten.
            #   This could be fixed by file locking, but a cross-platform
            #   implementation is certainly non-trivial.
            if len(lines) > 0:
                for line in lines:
                    if line.startswith(prefix):
                        if not matched and userline:
                            new_lines.append(userline + eol)
                        matched = True
                    elif line.endswith('\n'):
                        if eol == '\n':
                            new_lines.append(line)
                        else:
                            # restore eol
                            new_lines.append(line.rstrip('\n') + eol)
                    # make sure the last line has a newline
                    else:
                        new_lines.append(line + eol)
        except EnvironmentError, e:
            if e.errno == errno.ENOENT:
                # Ignore, when file doesn't exist and create it below.
                pass
            elif e.errno == errno.EACCES:
                raise TracError('The password file could not be read.  '
                                'Trac requires read and write access to both '
                                'the password file and its parent directory.')
            else:
                raise

        # Finally add the new line here, if it wasn't used before
        # to update or delete a line, creating content for a new file as well.
        if not matched and userline:
            new_lines.append(userline + eol)

        # Try to (re-)open file write-only now and save new content.
        try:
            f = open(filename, 'w')
            f.writelines(new_lines)
        except EnvironmentError, e:
            if e.errno == errno.EACCES:
                raise TracError('The password file could not be updated.  '
                                'Trac requires read and write access to both '
                                'the password file and its parent directory.')
            else:
                raise
        finally:
            if isinstance(f, file):
                # Close open file now, even after exception raised.
                f.close()
                if not f.closed:
                    self.log.debug('acct_mgr: _update_file() -- '
                                   'Closing file "%s" failed' % filename)
        return matched


class HtPasswdStore(AbstractPasswordFileStore):
    """Manages user accounts stored in Apache's htpasswd format.

    To use this implementation add the following configuration section to
    trac.ini:
    {{{
    [account-manager]
    password_store = HtPasswdStore
    password_file = /path/to/trac.htpasswd
    }}}
    """

    implements(IPasswordStore)

    def config_key(self):
        return 'htpasswd'

    def prefix(self, user):
        return user + ':'

    def userline(self, user, password):
        return self.prefix(user) + htpasswd(password)

    def _check_userline(self, user, password, suffix):
        return suffix == htpasswd(password, suffix)

    def _get_users(self, filename):
        f = open(filename, 'Ur')
        for line in f:
            user = line.split(':', 1)[0]
            if user:
                yield user.decode('utf-8')


class HtDigestStore(AbstractPasswordFileStore):
    """Manages user accounts stored in Apache's htdigest format.

    To use this implementation add the following configuration section to
    trac.ini:
    {{{
    [account-manager]
    password_store = HtDigestStore
    password_file = /path/to/trac.htdigest
    htdigest_realm = TracDigestRealm
    }}}
    """

    implements(IPasswordStore)

    realm = Option('account-manager', 'htdigest_realm', '')

    def config_key(self):
        return 'htdigest'

    def prefix(self, user):
        return '%s:%s:' % (user, self.realm.encode('utf-8'))

    def userline(self, user, password):
        return self.prefix(user) + htdigest(user, self.realm.encode('utf-8'), password)

    def _check_userline(self, user, password, suffix):
        return suffix == htdigest(user, self.realm.encode('utf-8'), password)

    def _get_users(self, filename):
        _realm = self.realm.encode('utf-8')
        f = open(filename)
        for line in f:
            args = line.split(':')[:2]
            if len(args) == 2:
                user, realm = args
                if realm == _realm and user:
                    yield user.decode('utf-8')

