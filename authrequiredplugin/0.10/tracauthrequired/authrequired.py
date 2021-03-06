# -*- coding: utf-8 -*-
#
# Copyright 2006 Anton Graham <bladehawke@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#  3. The name of the author may not be used to endorse or promote
#     products derived from this software without specific prior
#     written permission.

# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from trac.core import *
from trac.web.chrome import INavigationContributor

class AuthRequired(Component):
    """AuthRequiredPlugin
    Require anonymous users to authenticate using the form based login.
    This has been greatly simplified from the original implementation
    thanks to a hint from coderanger.
       """
    implements(INavigationContributor)

    # INavigationContributor methods

    def get_active_navigation_item(self, req):
        return 'AuthRequired'

    def get_navigation_items(self, req):
        if ((req.authname and req.authname != 'anonymous') or \
            req.path_info.startswith('/login') or \
            req.path_info.startswith('/reset_password') or \
            req.path_info.startswith('/register')):
            return []
        self.log.debug('Redirecting anonymous request to /login')
        #req.redirect(req.href.login())
        # Testing new redirect syntax.  Thanks to jfernandez@ist.psu.edu
        req.redirect(req.href.login(), {'referer':req.abs_href(req.path_info)})
        return [] # We don't really get here, but what the heck...

