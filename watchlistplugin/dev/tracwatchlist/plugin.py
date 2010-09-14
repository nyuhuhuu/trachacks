# -*- coding: utf-8 -*-
"""
 Watchlist Plugin for Trac
 Copyright (c) 2008-2009  Martin Scharrer <martin@scharrer-online.de>
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

from  pkg_resources          import  resource_filename
from  urllib                 import  quote_plus

from  genshi.builder         import  tag, Markup
from  trac.config            import  BoolOption
from  trac.core              import  *
from  trac.db                import  Table, Column, Index, DatabaseManager
from  trac.ticket.model      import  Ticket
#from  trac.ticket.web_ui     import  TicketModule
from  trac.ticket.api        import  TicketSystem
from  trac.util.datefmt      import  pretty_timedelta, to_datetime
from  trac.util.text         import  to_unicode
from  trac.web.api           import  IRequestFilter, IRequestHandler, \
                                     RequestDone, HTTPNotFound, HTTPBadRequest
from  trac.web.chrome        import  ITemplateProvider, add_ctxtnav, \
                                     add_link, add_script, add_notice, \
                                     Chrome
from  trac.util.text         import  obfuscate_email_address
from  trac.web.href          import  Href
from  trac.wiki.model        import  WikiPage
from  trac.util.datefmt      import  to_timestamp

from  tracwatchlist.api      import  BasicWatchlist, IWatchlistProvider
from  tracwatchlist.translation import  add_domain, _, N_, T_, t_, tag_, gettext, ngettext
from  tracwatchlist.render   import  render_property_diff

# Try to use babels format_datetime to localise date-times if possible.
# A fall back to tracs implementation strips the unsupported `locale` argument.
from  trac.util.datefmt      import  format_datetime as trac_format_datetime
try:
    from  babel.dates        import  format_datetime, LC_TIME
except ImportError:
    LC_TIME = None
    def format_datetime(t=None, format='%x %X', tzinfo=None, locale=None):
        return trac_format_datetime(t, format, tzinfo)

def ensure_tuple( var ):
    """Ensures that variable is a tuple, even if its a scalar"""
    if isinstance(var,tuple):
        return var
    if getattr(var, '__iter__', False):
        return tuple(var)
    return (var,)

class WatchlistPlugin(Component):
    """Main class of the Trac WatchlistPlugin.

    Displays watchlist for wiki pages, ticket and possible other Trac realms.

    For documentation see http://trac-hacks.org/wiki/WatchlistPlugin.
    """
    providers = ExtensionPoint(IWatchlistProvider)

    implements( IRequestHandler, IRequestFilter, ITemplateProvider ) 

    OPTIONS = {
        'notifications': ( False, N_("Notifications")),
        'display_notify_navitems': ( False, N_("Display notification navigation items")),
        'display_notify_column': ( True, N_("Display notification column in watchlist tables")),
        'notify_by_default': ( False, N_("Enable notifications by default for all watchlist entries")),
        'stay_at_resource': ( False, N_("The user stays at the resource after a watch/unwatch operation and the watchlist page is not displayed")),
        'stay_at_resource_notify': ( True, N_("The user stays at the resource after a notify/do-not-notify operation and the watchlist page is not displayed")),
        'show_messages_on_resource_page': ( True, N_("Action messages are shown on resource pages")),
        'show_messages_on_watchlist_page': ( True, N_("Action messages are shown when going to the watchlist page")),
        'show_messages_while_on_watchlist_page': ( True, N_("Show action messages while on watchlist page")),
        'autocomplete_inputs': ( True, N_("Autocomplete input fields (add/remove resources)")),
        'dynamic_tables': ( True, N_("Dynamic watchlist tables")),
        'individual_column_filtering': ( True, N_("Individual column filtering")),
    }

    global_options = [ BoolOption('watchlist',name,data[0],doc=data[1]) for (name,data) in OPTIONS.iteritems() ]

    wsub = None

    def __init__(self):
      self.realms = []
      self.realm_handler = {}

      # bind the 'watchlist' catalog to the specified locale directory
      locale_dir = resource_filename(__name__, 'locale')
      add_domain(self.env.path, locale_dir)

      for provider in self.providers:
        for realm in provider.get_realms():
          assert realm not in self.realms
          self.realms.append(realm)
          self.realm_handler[realm] = provider
          #self.log.debug("realm: %s %s" % (realm, str(provider)))

      try:
          # Import methods from WatchSubscriber of the AnnouncerPlugin
          from  announcerplugin.subscribers.watchers  import  WatchSubscriber
          self.wsub = self.env[WatchSubscriber]
          if self.wsub:
            self.log.debug("WS: WatchSubscriber found in announcerplugin")
      except Exception, e:
          try:
            # Import fallback methods for AnnouncerPlugin's dev version
            from  announcer.subscribers.watchers  import  WatchSubscriber
            self.wsub = self.env[WatchSubscriber]
            if self.wsub:
              self.log.debug("WS: WatchSubscriber found in announcer")
          except Exception, ee:
            self.log.debug("WS! " + str(e))
            self.log.debug("WS! " + str(ee))
            self.wsub = None


    def _handle_settings(self, req, settings):
        newoptions = req.args.get('options',[])
        for k in settings['useroptions'].keys():
          settings['useroptions'][k] = k in newoptions
        for realm in self.realms:
          try:
            settings['useroptions'][realm + '_fields'] = req.args.get(realm + '_fields')
          except:
            pass
        self._save_user_settings(req.authname, settings)
        # Clear session cache for nav items
        try:
            del req.session['watchlist_display_notify_navitems']
        except:
            pass

    def get_settings(self, user):
        settings = {}
        settings['useroptions'] = dict([
            ( name,self.config.getbool('watchlist',name) ) for name in self.OPTIONS.keys() ])
        usersettings = self._get_user_settings(user)
        settings['useroptions'].update( usersettings['useroptions'] )
        del usersettings['useroptions']
        settings.update( usersettings )
        return settings

    def is_notify(self, req, realm, resid):
      try:
        return self.wsub.is_watching(req.session.sid, True, realm, resid)
      except AttributeError:
        return False
      except Exception, e:
        self.log.error("is_notify error: " + str(e))
        return False

    def set_notify(self, req, realm, resid):
      try:
        self.wsub.set_watch(req.session.sid, True, realm, resid)
      except AttributeError:
        return False
      except Exception, e:
        self.log.error("set_notify error: " + str(e))

    def unset_notify(self, req, realm, resid):
      try:
        self.wsub.set_unwatch(req.session.sid, True, realm, resid)
      except AttributeError:
        return False
      except Exception, e:
        self.log.error("unset_notify error: " + str(e))

    def _get_sql_names_and_patterns(self, nameorpatternlist):
      import re
      if not nameorpatternlist:
        return [], []
      star  = re.compile(r'(?<!\\)\*')
      ques  = re.compile(r'(?<!\\)\?')
      names = []
      patterns = []
      for norp in nameorpatternlist:
        norp = norp.strip()
        pattern = norp.replace('%',r'\%').replace('_',r'\_')
        pattern_unsub = pattern
        pattern = star.sub('%', pattern)
        pattern = ques.sub('_', pattern)
        if pattern == pattern_unsub:
          names.append(norp)
        else:
          pattern = pattern.replace('\*','*').replace('\?','?')
          patterns.append(pattern)
      return names, patterns

    def _sql_pattern_unescape(self, pattern):
      import re
      percent    = re.compile(r'(?<!\\)%')
      underscore = re.compile(r'(?<!\\)_')
      pattern = pattern.replace('*','\*').replace('?','\?')
      pattern = percent.sub('*', pattern)
      pattern = underscore.sub('?', pattern)
      pattern = pattern.replace('\%','%').replace('\_','_')
      return pattern

    def _convert_pattern(self, pattern):
        # needs more work, excape sequences, etc.
        return pattern.replace('*','%').replace('?','_')

    def get_watched_resources(self, realm, user, db=None):
        """Yields list of resourses watch by the given user in the given realm."""
        if not db:
            db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
        SELECT resid
            FROM watchlist
        WHERE realm=%s AND wluser=%s
        """, (realm, user)
        )
        for values in cursor.fetchall():
            yield values[0]

    ### methods for IRequestHandler
    def match_request(self, req):
        return req.path_info.startswith("/watchlist")

    def _save_user_settings(self, user, settings):
        """Saves user settings in 'watchlist_settings' table.
           Only saving of all user settings is supported at the moment."""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.log = self.log
        options = settings['useroptions']
        self.log.debug("WL options: " + unicode(options))

        settingsstr = "&".join([ "=".join([k,unicode(v)]) for k,v in options.iteritems()])

        cursor.execute("""
          SELECT count(*)
            FROM watchlist_settings
           WHERE wluser=%s
           LIMIT 0,1
        """, (user,)
        )
        ex = cursor.fetchone()
        if not ex or not int(ex[0]):
          cursor.execute("""
            INSERT
              INTO watchlist_settings (wluser,name,type,settings)
            VALUES (%s,'useroptions','ListOfBool',%s)
          """, (user, settingsstr)
          )
        else:
          cursor.execute("""
            UPDATE watchlist_settings
               SET settings=%s,name='useroptions',type='ListOfBool'
             WHERE wluser=%s
          """, (settingsstr, user)
          )

        db.commit()
        return True

    def _get_user_settings(self, user):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
          SELECT settings
            FROM watchlist_settings
           WHERE wluser=%s AND name='useroptions'
        """, (user,))

        try:
          def strtoval (val):
            if   val == 'True':
              return True
            elif val == 'False':
              return False
            else:
              return val
          (settingsstr,) = cursor.fetchone()
          #self.log.debug("WL SET: " + settingsstr)
          d = dict([
              (k,strtoval(v)) for k,v in [ kv.split('=') for kv in settingsstr.split("&") ]
          ])
          #self.log.debug("WL SETd: " + unicode(d))
          return dict(useroptions=d)
        except Exception, e:
          #self.log.debug("WL get user settings: " + unicode(e))
          return dict(useroptions=dict())

    def process_request(self, req):
        user  = to_unicode( req.authname )
        realm = to_unicode( req.args.get('realm', u'') )
        resid = req.args.get('resid', u'')
        resids = []
        if not isinstance(resid,(list,tuple)):
          resid = [resid]
        for r in resid:
          resids.extend(r.replace(',',' ').split())
        action = req.args.get('action','view')
        names,patterns = self._get_sql_names_and_patterns( resids )
        single = len(names) == 1 and not patterns
        async = req.args.get('async', 'false') == 'true'

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        if not user or user == 'anonymous':
            # TRANSLATOR: Link part of
            # "Please %(log_in)s to view or change your watchlist"
            log_in=tag.a(_("log in"), href=req.href('login'))
            if tag_ == None:
                # For Trac 0.11
                raise HTTPNotFound(
                        tag("Please ", log_in, " to view or change your watchlist"))
            else:
                # For Trac 0.12
                raise HTTPNotFound(
                        tag_("Please %(log_in)s to view or change your watchlist",
                            log_in=log_in))

        wldict = req.args.copy()
        wldict['action'] = action

        settings = self.get_settings( user )
        options = settings['useroptions']
        # Needed here to get updated settings
        if action == "save":
          self._handle_settings(req, settings)
          action = "view"

        settings = self.get_settings( user )
        options = settings['useroptions']
        wldict['perm']   = req.perm
        wldict['realms'] = self.realms
        wldict['error']  = False
        wldict['notifications'] = bool(self.wsub and options['notifications'] and options['display_notify_column'])
        wldict['OPTIONS'] = self.OPTIONS
        wldict['options'] = options
        wldict['lastvisit'] = 0
        wldict['wlgettext'] = gettext
        wldict['t_'] = t_
        wldict['available_fields'] = {}
        wldict['default_fields'] = {}
        #wldict['label'] = dict([ self.realm_handler for r in self.realms ])
        def get_label(realm, n_plural=1):
            return self.realm_handler[realm].get_realm_label(realm, n_plural)
        wldict['get_label'] = get_label

        for r in self.realms:
            wldict['available_fields'][r],wldict['default_fields'][r] = self.realm_handler[r].get_fields(r)
        wldict['active_fields'] = {}
        for r in self.realms:
            cols = options.get(r + '_fields','').split(',')
            #self.log.debug( "WL SC = " + unicode(cols) )
            if not cols or cols == ['']:
                cols = wldict['default_fields'].get(r,[])
                #self.log.debug( "WL EC = " + unicode(cols) )
            wldict['active_fields'][r] = cols
        #self.log.debug( "WL DC = " + unicode(wldict['default_fields']) )
        #self.log.debug( "WL AC = " + unicode(wldict['active_fields']) )

        onwatchlistpage = req.environ.get('HTTP_REFERER','').find(
                          req.href.watchlist()) != -1
        redirectback = options['stay_at_resource'] and single and not onwatchlistpage
        redirectback_notify = options['stay_at_resource_notify'] and single and not \
                              onwatchlistpage

        if onwatchlistpage:
          wldict['show_messages'] = options['show_messages_while_on_watchlist_page']
        else:
          wldict['show_messages'] = options['show_messages_on_watchlist_page']

        new_res = []
        del_res = []
        alw_res = []
        err_res = []
        err_pat = []
        if action == "watch":
          handler = self.realm_handler[realm]
          if names:
            reses = list(handler.res_list_exists(realm, names))

            sql = ("""
              SELECT resid
                FROM watchlist
               WHERE wluser=%s AND realm=%s AND
                     resid IN (
            """ + ",".join(("%s",) * len(names)) + ")"
            )
            cursor.execute( sql, [user,realm] + names)
            alw_res = [ res[0] for res in cursor.fetchall() ]
            new_res.extend(set(reses).difference(alw_res))
            err_res.extend(set(names).difference(reses))
          for pattern in patterns:
            reses = list(handler.res_pattern_exists(realm, pattern))

            if not reses:
              err_pat.append(self._sql_pattern_unescape(pattern))
            else:
              cursor.execute("""
                SELECT resid
                  FROM watchlist
                 WHERE wluser=%s AND realm=%s AND resid LIKE (%s)
              """, (user,realm,pattern)
              )
              watched_res = [ res[0] for res in cursor.fetchall() ]
              alw_res.extend(set(reses).intersection(watched_res))
              new_res.extend(set(reses).difference(alw_res))

          if new_res:
            #cursor.log = self.log
            cursor.executemany("""
              INSERT
                INTO watchlist (wluser, realm, resid)
              VALUES (%s,%s,%s)
            """, [(user, realm, res) for res in new_res]
            )
            db.commit()

          action = "view"
          if options['show_messages_on_resource_page'] and not onwatchlistpage and redirectback:
            req.session['watchlist_message'] = _(
              "You are now watching this resource."
            )
          if self.wsub and options['notifications'] and options['notify_by_default']:
            for res in new_res:
              self.set_notify(req, realm, res)
            db.commit()
          if redirectback:
            req.redirect(req.href(realm,names[0]))
            raise RequestDone

        elif action == "unwatch":
          if names:
            sql = ("""
              SELECT resid
                FROM watchlist
               WHERE wluser=%s AND realm=%s AND
                     resid IN (
            """ + ",".join(("%s",) * len(names)) + ")"
            )
            cursor.execute( sql, [user,realm] + names)
            reses = [ res[0] for res in cursor.fetchall() ]
            del_res.extend(reses)
            err_res.extend(set(names).difference(reses))

            sql = ("""
              DELETE
                FROM watchlist
               WHERE wluser=%s AND realm=%s AND
                     resid IN (
            """ + ",".join(("%s",) * len(names)) + ")"
            )
            cursor.execute( sql, [user,realm] + names)
          for pattern in patterns:
            cursor.execute("""
              SELECT resid
                FROM watchlist
               WHERE wluser=%s AND realm=%s AND resid LIKE %s
            """, (user,realm,pattern)
            )
            reses = [ res[0] for res in cursor.fetchall() ]
            if not reses:
              err_pat.append(self._sql_pattern_unescape(pattern))
            else:
              del_res.extend(reses)
              cursor.execute("""
                DELETE
                  FROM watchlist
                 WHERE wluser=%s AND realm=%s AND resid LIKE %s
              """, (user,realm,pattern)
              )
          db.commit()

          action = "view"
          if options['show_messages_on_resource_page'] and not onwatchlistpage and redirectback:
            req.session['watchlist_message'] = _(
              "You are no longer watching this resource."
            )
          if self.wsub and options['notifications'] and options['notify_by_default']:
            for res in del_res:
              self.unset_notify(req, realm, res)
            db.commit()
          if redirectback:
            req.redirect(req.href(realm,names[0]))
            raise RequestDone

        wldict['del_res'] = del_res
        wldict['err_res'] = err_res
        wldict['err_pat'] = err_pat
        wldict['new_res'] = new_res
        wldict['alw_res'] = alw_res

        if action == "notifyon":
            if single and not self.res_exists(realm, resids[0]):
                raise HTTPNotFound(t_("Page %(name)s not found", name=resids[0]))
            if self.wsub and options['notifications']:
              for res in resids:
                if self.res_exists(realm, res):
                  self.set_notify(req, realm, res)
              db.commit()
            if redirectback_notify and not async:
              if options['show_messages_on_resource_page']:
                req.session['watchlist_notify_message'] = _(
                  """
                  You are now receiving change notifications
                  about this resource.
                  """
                )
              req.redirect(req.href(realm,resids[0]))
              raise RequestDone
            action = "view"
        elif action == "notifyoff":
            if self.wsub and options['notifications']:
              for res in resids:
                self.unset_notify(req, realm, res)
              db.commit()
            if redirectback_notify and not async:
              if options['show_messages_on_resource_page']:
                req.session['watchlist_notify_message'] = _(
                  """
                  You are no longer receiving
                  change notifications about this resource.
                  """
                )
              req.redirect(req.href(realm,resids[0]))
              raise RequestDone

            action = "view"

        if action == "search":
          handler = self.realm_handler[realm]
          query = req.args.get('q', u'')
          found = handler.res_pattern_exists(realm, query + '%')

          watched = self.get_watched_resources( realm, user )
          notwatched = list(set(found).difference(set(watched)))
          notwatched.sort()
          req.send( unicode('\n'.join(notwatched) + '\n').encode("utf-8"), 'text/plain', 200 )
          raise RequestDone


        if async:
          req.send("",'text/plain', 200)
          raise RequestDone

        if action == "view":
            for (xrealm,xhandler) in self.realm_handler.iteritems():
              if xhandler.has_perm(xrealm, req.perm):
                wldict[xrealm + 'list'] = xhandler.get_list(xrealm, self, req, set(wldict['active_fields'][xrealm]))
                name = xhandler.get_realm_label(xrealm, n_plural=1000)
                # TRANSLATOR: Navigation link to point to watchlist section of this realm
                # (e.g. 'Wikis', 'Tickets').
                add_ctxtnav(req, _("Watched %(realm_plural)s", realm_plural=name),
                            href=req.href('watchlist') + '#' + name)
            return ("watchlist.html", wldict, "text/html")
        else:
            raise HTTPBadRequest(_("Invalid watchlist action '%(action)s'!", action=action))


    def has_watchlist(self, user):
        """Checks if user has a non-empty watchlist."""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
          SELECT count(*)
            FROM watchlist
           WHERE wluser=%s;
        """, (user,)
        )
        count = cursor.fetchone()
        if not count or not count[0]:
            return False
        else:
            return True

    def res_exists(self, realm, resid):
        return self.realm_handler[realm].res_exists(realm, resid)

    def is_watching(self, realm, resid, user):
        """Checks if user watches the given element."""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
          SELECT count(*)
            FROM watchlist
           WHERE realm=%s AND resid=%s AND wluser=%s;
        """, (realm, to_unicode(resid), user)
        )
        count = cursor.fetchone()
        if not count or not count[0]:
            return False
        else:
            return True

    ### methods for IRequestFilter
    def post_process_request(self, req, template, data, content_type):
        # Extract realm and resid from path:
        parts = req.path_info[1:].split('/',1)

        # Handle special case for '/' and '/wiki'
        if len(parts) == 0 or not parts[0]:
            parts = ["wiki", "WikiStart"]
        elif len(parts) == 1:
            parts.append("WikiStart")

        realm, resid = parts[:2]

        if realm not in self.realms or not \
                self.realm_handler[realm].has_perm(realm, req.perm):
            return (template, data, content_type)

        user  = to_unicode( req.authname )

        notify = 'False'
        # The notification setting is stored in the session to avoid rereading the whole
        # user settings for every page displayed
        try:
            notify = req.session['watchlist_display_notify_navitems']
        except KeyError:
            settings = self.get_settings(user)
            options = settings['useroptions']
            notify = (self.wsub and options['notifications'] and options['display_notify_navitems']) and 'True' or 'False'
            req.session['watchlist_display_notify_navitems'] = notify

        try:
            add_notice(req, req.session['watchlist_message'])
            del req.session['watchlist_message']
        except KeyError:
            pass
        try:
            add_notice(req, req.session['watchlist_notify_message'])
            del req.session['watchlist_notify_message']
        except KeyError:
            pass

        href = Href(req.base_path)
        user = req.authname
        if user and user != "anonymous":
            if self.is_watching(realm, resid, user):
                add_ctxtnav(req, _("Unwatch"),
                    href=req.href('watchlist', action='unwatch',
                    resid=resid, realm=realm),
                    title=_("Remove %(document)s from watchlist", document=realm))
            else:
                add_ctxtnav(req, _("Watch"),
                    href=req.href('watchlist', action='watch',
                    resid=resid, realm=realm),
                    title=_("Add %(document)s to watchlist", document=realm))
            if notify == 'True':
              if self.is_notify(req, realm, resid):
                add_ctxtnav(req, _("Do not Notify me"),
                    href=req.href('watchlist', action='notifyoff',
                    resid=resid, realm=realm),
                    title=_("Do not notify me if %(document)s changes", document=realm))
              else:
                add_ctxtnav(req, _("Notify me"),
                    href=req.href('watchlist', action='notifyon',
                    resid=resid, realm=realm),
                    title=_("Notify me if %(document)s changes", document=realm))

        return (template, data, content_type)


    def pre_process_request(self, req, handler):
        return handler

    # ITemplateProvider methods:
    def get_htdocs_dirs(self):
        return [('watchlist', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return [ resource_filename(__name__, 'templates') ]



class WikiWatchlist(BasicWatchlist):
    """Watchlist entry for wiki pages."""
    realms = ['wiki']
    fields = {'wiki':{
        'changetime': T_("Modified"),
        'author'    : T_("Author"),
        'version'   : T_("Version"),
        'diff'      : T_("Diff"),
        'history'   : T_("History"),
        # TRANSLATOR: Abbreviated label for 'unwatch' column header.
        # Should be a single character to not widen the column.
        'unwatch'   : N_("U"),
        # TRANSLATOR: Label for 'notify' column header.
        # Should tell the user that notifications can be switched on or off
        # with the check-boxes in this column.
        'notify'    : N_("Notify"),
        'comment'   : T_("Comment"),

        'readonly'  : N_("read-only"),
        # T#RANSLATOR: IP = Internet Protocol (address)
        #'ipnr'      : N_("IP"), # Note: not supported by Trac 0.12 WikiPage class
    }}
    default_fields = {'wiki':[
        'name', 'changetime', 'author', 'version', 'diff',
        'history', 'unwatch', 'notify', 'comment',
    ]}

    def __init__(self):
        self.fields['wiki']['name'] = self.get_realm_label('wiki')

    def get_realm_label(self, realm, n_plural=1):
      return ngettext("Wiki Page", "Wiki Pages", n_plural)

    def res_exists(self, realm, resid):
      return WikiPage(self.env, resid).exists

    def res_pattern_exists(self, realm, pattern):
      db = self.env.get_db_cnx()
      cursor = db.cursor()
      cursor.execute("""
        SELECT name
          FROM wiki
         WHERE name
          LIKE (%s)
      """, (pattern,)
      )
      return [ vals[0] for vals in cursor.fetchall() ]

    def get_list(self, realm, wl, req, fields=None):
      db = self.env.get_db_cnx()
      cursor = db.cursor()
      user = req.authname
      locale = getattr( req, 'locale', LC_TIME)
      wikilist = []

      for name in wl.get_watched_resources( 'wiki', req.authname ):
          wikipage = WikiPage(self.env, name, db=db)
          wikidict = {}

          if not wikipage.exists:
            wikidict['deleted'] = True
            if 'name' in fields:
                wikidict['name'] = name
            if 'author' in fields:
                wikidict['author'] = '?'
            if 'changetime' in fields:
                wikidict['changetime'] = '?'
                wikidict['ichangetime'] = 0
            if 'comment' in fields:
                wikidict['comment'] = tag.strong(t_("deleted"), class_='deleted')
            if 'notify' in fields:
                wikidict['notify'] =  wl.is_notify(req, 'wiki', name)
            wikilist.append(wikidict)
            continue

          if 'name' in fields:
              wikidict['name'] = name
          if 'author' in fields:
              if not (Chrome(self.env).show_email_addresses or 
                      'EMAIL_VIEW' in req.perm(wikipage.resource)):
                  wikidict['author'] = obfuscate_email_address(wikipage.author)
              else:
                  wikidict['author'] = wikipage.author
          if 'version' in fields:
              wikidict['version'] = unicode(wikipage.version)
          if 'changetime' in fields:
              wikidict['changetime'] = format_datetime( wikipage.time, locale=locale )
              wikidict['ichangetime'] = to_timestamp( wikipage.time )
              wikidict['timedelta'] = pretty_timedelta( wikipage.time )
              wikidict['timeline_link'] = req.href.timeline(precision='seconds',
                  from_=trac_format_datetime ( wikipage.time, 'iso8601'))
          if 'comment' in fields:
              comment = wikipage.comment or ""
              if len(comment) > 200:
                  comment = moreless(comment, 200)
              wikidict['comment'] = comment
          if 'notify' in fields:
              wikidict['notify']   = wl.is_notify(req, 'wiki', name)
          if 'readonly' in fields:
              wikidict['readonly'] = wikipage.readonly and t_("yes") or t_("no")
          #if 'ipnr' in fields:
          #    wikidict['ipnr'] = wikipage.ipnr,  # Note: Not supported by Trac 0.12
          wikilist.append(wikidict)
      return wikilist



class TicketWatchlist(BasicWatchlist):
    """Watchlist entry for tickets."""
    realms = ['ticket']
    fields = {'ticket':{
        'author'    : T_("Author"),
        'changes'   : N_("Changes"),
        # TRANSLATOR: '#' stands for 'number'.
        # This is the header label for a column showing the number
        # of the latest comment.
        'commentnum': N_("Comment #"),
        'unwatch'   : N_("U"),
        'notify'    : N_("Notify"),
        'comment'   : T_("Comment"),
        # Plus further pairs imported at __init__.
    }}

    default_fields = {'ticket':[
        'id', 'changetime', 'author', 'changes', 'commentnum',
        'unwatch', 'notify', 'comment',
    ]}

    def __init__(self):
        try: # Only works for Trac 0.12, but is not needed for Trac 0.11 anyway
            self.fields['ticket'].update( TicketSystem(self.env).get_ticket_field_labels() )
        except AttributeError:
            pass
        self.fields['ticket']['id'] = self.get_realm_label('ticket')

    def get_realm_label(self, realm, n_plural=1):
        return ngettext("Ticket", "Tickets", n_plural)

    def res_exists(self, realm, resid):
      try:
        return Ticket(self.env, int(resid)).exists
      except:
        return False

    def res_pattern_exists(self, realm, pattern):
      if pattern == '%':
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
          SELECT id
            FROM ticket
        """
        )
        return [ vals[0] for vals in cursor.fetchall() ]
      else:
        return []

    def get_list(self, realm, wl, req, fields=None):
      db = self.env.get_db_cnx()
      cursor = db.cursor()
      ticketlist = []
      for id in wl.get_watched_resources( 'ticket', req.authname ):
          sid = unicode(id)
          ticket = Ticket(self.env, id, db)

          render_elt = lambda x: x
          if not (Chrome(self.env).show_email_addresses or \
                  'EMAIL_VIEW' in req.perm(ticket.resource)):
              render_elt = obfuscate_email_address

          ticketdict = {}
          # Copy all requested fields from ticket
          if fields:
              for f in fields:
                  ticketdict[f] = ticket.values.get(f,u'')
          else:
              ticketdict = ticket.values.copy()

          # Changes are special. Comment, commentnum and last author are included in them.
          if 'changes' in fields or 'comment' in fields or 'commentnum' in fields or 'author' in fields:
            changes = []
            # If there are now changes the reporter is the last author
            author  = ticket.values['reporter']
            commentnum = u"0"
            comment = u""
            want_changes = 'changes' in fields
            for date,cauthor,field,oldvalue,newvalue,permanent in ticket.get_changelog(ticket.time_changed,db):
                author = cauthor
                if field == 'comment':
                    if 'commentnum' in fields:
                        ticketdict['commentnum'] = to_unicode(oldvalue)
                    if 'comment' in fields:
                        comment = to_unicode(newvalue)
                        if len(comment) > 200:
                            comment = moreless(comment, 200)
                        ticketdict['comment'] = comment
                    if not want_changes:
                        break
                else:
                    if want_changes:
                      changes.extend(
                        [ tag(tag.strong(self.fields['ticket'][field]), ' ',
                            render_property_diff(self.env, req, ticket, field, oldvalue, newvalue)
                            ), tag('; ') ])
            if want_changes:
                # Remove the last tag('; '):
                if changes:
                    changes.pop()
                if len(changes) > 5:
                    changes = moreless(changes, 5)
                ticketdict['changes'] = tag(changes)

          locale = getattr( req, 'locale', LC_TIME)
          if 'id' in fields:
              ticketdict['id'] = sid
          if 'cc' in fields:
              if render_elt == obfuscate_email_address:
                ticketdict['cc'] = ', '.join([ render_elt(c) for c in ticketdict['cc'].split(', ') ])
          if 'author' in fields:
              ticketdict['author'] = render_elt(author),
          if 'changetime' in fields:
              changetime = ticket.time_changed
              ticketdict.update(
                  changetime       = format_datetime( changetime, locale=locale ),
                  ichangetime      = to_timestamp( changetime ),
                  changetime_delta = pretty_timedelta( changetime ),
                  changetime_link  = req.href.timeline(precision='seconds',
                                     from_=trac_format_datetime ( changetime, 'iso8601')))
          if 'time' in fields:
              time = ticket.time_created
              ticketdict.update(
                  time             = format_datetime( time, locale=locale ),
                  itime            = to_timestamp( time ),
                  time_delta       = pretty_timedelta( time ),
                  time_link        = req.href.timeline(precision='seconds',
                                     from_=trac_format_datetime ( time, 'iso8601')))
          if 'description' in fields:
              description = ticket.values['description']
              if len(description) > 200:
                  description = moreless(description, 200)
              ticketdict['description'] = description
          if 'notify' in fields:
              ticketdict['notify'] = wl.is_notify(req, 'ticket', sid)
          if 'owner' in fields:
              ticketdict['owner'] = render_elt(ticket.values['owner'])
          if 'reporter' in fields:
              ticketdict['reporter'] = render_elt(ticket.values['reporter'])

          ticketlist.append(ticketdict)
      return ticketlist


def moreless(text, length):
    return tag(tag.span(text[:length]),tag.a(' [', tag.strong(Markup('&hellip;')), ']', class_="more"),
        tag.span(text[length:],class_="moretext"),tag.a(' [', tag.strong('-'), ']', class_="less"))


