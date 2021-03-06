# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Sergio Talens-Oliag <sto@iti.es>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
TracPermissionFilter

Plugin to remove Trac permissions using a blacklist and/or a whitelist.

This hack was born to be able to archive projects without touching the Trac
database, the idea is to use the filter to disable all permissions that allow
users to modify it without changing their permissions on the database and be
able to restore the project to the original state simply disabling the filter.

To filter permissions as desired the plugin has to be the first one on the
permission_policy list and it works as follows:

1. If the blacklist is available and the permission being considered is on
   the list the check_permission function returns False and the permission
   evaluation stops. 

2. If the whitelist is available and the permission we are checking is
   not on the list the check_permission function returns False and the
   permission evaluation stops. 

3. If the evaluation gets here the permission is ignored by the
   plugin and the next permission policy is checked. 

If the boolean option `adminmeta` is True the filters are ignored for users
with TRAC_ADMIN permission.
"""

from trac.config import BoolOption,ListOption
from trac.core import *
from trac.perm import IPermissionPolicy

__all__ = ['PermissionFilter']

class PermissionFilter(Component):
    implements(IPermissionPolicy)
    adminmeta = BoolOption(
        'permission-filter', 'adminmeta', True,
        doc="""If this option is set to True (the default) the filters don't
        affect a user with TRAC_ADMIN permission. Note that if the variable is
        set to False filtering has odd effects on users with TRAC_ADMIN
        permission because we reject based on action name and TRAC_ADMIN is
        usually not checked directly"""
    )
    blacklist = ListOption(
        'permission-filter', 'blacklist', '',
        doc="""List of invalid permissions, the ones listed here are always False"""
    )
    whitelist = ListOption(
        'permission-filter', 'whitelist', '',
        doc="""List of valid permissions, the ones not listed here are always False"""
    )
    def check_permission(self, action, username, resource, perm):
        _admin = False
        if self.adminmeta:
            if action == 'TRAC_ADMIN':
		return
            elif 'TRAC_ADMIN' in perm:
                _admin = True
        if self.blacklist and len(self.blacklist) != 0:
            if not _admin and action in self.blacklist:
                return False
        if self.whitelist and len(self.whitelist) != 0:
            if not _admin and action not in self.whitelist:
                return False
        return 
