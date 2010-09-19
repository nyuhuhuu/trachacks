# -*- coding: utf-8 -*-
"""
 Watchlist Plugin for Trac
 Copyright (c) 2008-2010  Martin Scharrer <martin@scharrer-online.de>
 This is Free Software under the BSD license.

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__url__      = ur"$URL$"[6:-2]
__author__   = ur"$Author$"[9:-2]
__revision__ = int("0" + ur"$Rev$"[6:-2].strip('M'))
__date__     = ur"$Date$"[7:-2]

# Import translation functions. Fallbacks are provided for Trac 0.11.
try:
    from  trac.util.translation  import  domain_functions
    add_domain, _, N_, tag_, gettext, ngettext = \
        domain_functions('watchlist', ('add_domain', '_', 'N_', 'tag_', 'gettext', 'ngettext'))
except ImportError:
    from  trac.util.translation  import  gettext, ngettext
    _, N_, tag_  = gettext, gettext, None
    def add_domain(a,b,c=None):
        pass

# Import tracs `N_` as `T_` to mark strings already translated by trac.
# Note: Later this might also be needed for `_`.
try:
    from  trac.util.translation  import  N_ as T_
    from  trac.util.translation  import   _ as t_
except:
    T_ = N_
    t_ =  _

# EOF
