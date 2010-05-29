"""
 Wattchlist Plugin for Trac
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

from trac.core import *

from  genshi.builder     import  tag, Markup
from  trac.config        import  BoolOption
from  trac.db            import  Table, Column, Index, DatabaseManager
from  trac.ticket.model  import  Ticket
from  trac.util          import  format_datetime, pretty_timedelta
from  trac.util.text     import  to_unicode
from  trac.web.api       import  IRequestFilter, IRequestHandler, RequestDone
from  trac.web.chrome    import  ITemplateProvider, add_ctxtnav, add_link, add_script, add_notice
from  trac.web.href      import  Href
from  trac.wiki.model    import  WikiPage
from  urllib             import  quote_plus
from  tracwatchlist.api  import  IWatchlistProvider

__DB_VERSION__ = 3

class WatchlistError(TracError):
    show_traceback = False
    title = 'Watchlist Error'


class WatchlistPlugin(Component):
    """For documentation see http://trac-hacks.org/wiki/WatchlistPlugin"""
    providers = ExtensionPoint(IWatchlistProvider)


    implements( IRequestHandler, IRequestFilter, ITemplateProvider )
    gnotifyu = BoolOption('watchlist', 'notifications', False,
                "Enables notification features")
    gnotifyctxtnav = BoolOption('watchlist', 'display_notify_navitems', False,
                "Enables notification navigation items")
    gnotifycolumn = BoolOption('watchlist', 'display_notify_column', True,
                "Enables notification column in watchlist tables")
    gnotifybydefault = BoolOption('watchlist', 'notify_by_default', False,
                "Enables notifications by default for all watchlist entries")
    gredirectback = BoolOption('watchlist', 'stay_at_resource', False,
                "The user stays at the resource after a watch/unwatch operation "
                "and the watchlist page is not displayed.")
    gmsgrespage = BoolOption('watchlist', 'show_messages_on_resource_page', True, 
                "Enables action messages on resource pages.")
    gmsgwlpage  = BoolOption('watchlist', 'show_messages_on_watchlist_page', True, 
                "Enables action messages when going to the watchlist page.")
    gmsgwowlpage = BoolOption('watchlist', 'show_messages_while_on_watchlist_page', True, 
                "Enables action messages while on watchlist page.")


    if gnotifyu:
      try:
        # Import methods from WatchSubscriber from the AnnouncerPlugin
        from  announcerplugin.subscribers.watchers  import  WatchSubscriber
        is_notify    = WatchSubscriber.__dict__['is_watching']
        set_notify   = WatchSubscriber.__dict__['set_watch']
        unset_notify = WatchSubscriber.__dict__['set_unwatch']
        set_unwatch  = unset_notify
      except:
        gnotify = False
      else:
        gnotify = True

    # Per user setting # FTTB FIXME
    notifyctxtnav = gnotifyctxtnav

    def __init__(self):
      self.realms = []
      self.realm_handler = {}
      for provider in self.providers:
        for realm in provider.get_realms():
          assert realm not in self.realms
          self.realms.append(realm)
          self.realm_handler[realm] = provider
          self.env.log.debug("realm: %s %s" % (realm, str(provider)))


    def _convert_pattern(self, pattern):
        # needs more work, excape sequences, etc.
        return pattern.replace('*','%').replace('?','_')

    ### methods for IRequestHandler
    def match_request(self, req):
        return req.path_info.startswith("/watchlist")

    def _save_user_settings(self, user, settings):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        #cursor.log = self.env.log

        settingsstr = "&".join([ "=".join(kv) for kv in settings.items()])

        cursor.execute( """
          SELECT count(*) FROM watchlist_settings WHERE wluser=%s LIMIT 0,1""", (user,) )
        ex = cursor.fetchone()
        if not ex or not int(ex[0]):
          cursor.execute(
              "INSERT INTO watchlist_settings VALUES (%s,%s)",
              (user, settingsstr) )
        else:
          cursor.execute(
              "UPDATE watchlist_settings SET settings=%s WHERE wluser=%s ",
              (settingsstr, user) )

        db.commit()
        return True

    def _get_user_settings(self, user):
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute(
            "SELECT settings FROM watchlist_settings WHERE wluser = %s",
            (user,) )

        try:
          (settingsstr,) = cursor.fetchone()
          return dict([ kv.split('=') for kv in settingsstr.split("&") ])
        except:
          return dict()


    def process_request(self, req):
        href = req.href
        user = to_unicode( req.authname )
        if not user or user == 'anonymous':
            raise WatchlistError(
                    tag( "Please ", tag.a("log in", href=href('login')),
                        " to view or change your watchlist!" ) )

        args = req.args
        wldict = args.copy()
        action = args.get('action','view')
        redirectback = self.gredirectback
        ispattern = False# Disabled for now, not implemented fully # args.get('ispattern','0')
        onwatchlistpage = req.environ.get('HTTP_REFERER','').find(href.watchlist()) != -1

        if ispattern or onwatchlistpage:
          redirectback = False

        if action in ('watch','unwatch','notifyon','notifyoff'):
            try:
                realm = to_unicode( args['realm'] )
                resid = to_unicode( args['resid'] )
            except KeyError:
                raise WatchlistError("Realm and ResId needed for watch/unwatch action!")
            if realm not in self.realms:
                raise WatchlistError("Realm '%s' is not supported by the watchlist! Maybe you need to install and enable a watchlist extension for it first?")
            is_watching = self.is_watching(realm, resid, user)
            realm_perm   = self.realm_handler[realm].has_perm(req.perm)
            if ispattern:
              pattern = self._convert_pattern(resid)
            else:
              reslink = href(realm,resid)
              res_exists  = self.res_exists(realm, resid)
        else:
            is_watching = None

        wlhref = href("watchlist")
        for (xrealm,handler) in self.realm_handler.iteritems():
          name = handler.get_realm_label(xrealm, plural=True)
          add_ctxtnav(req, "Watched " + name.capitalize(), href=wlhref + '#' + name)
        #add_ctxtnav(req, "Settings", href=wlhref + '#settings')

        wldict['perm'] = req.perm
        wldict['realms'] = self.realms
        wldict['error'] = False
        wldict['notify'] = self.gnotify and self.gnotifycolumn
        if onwatchlistpage:
          wldict['show_messages'] = self.gmsgwowlpage
        else:
          wldict['show_messages'] = self.gmsgwlpage
        msgrespage = self.gmsgrespage

        # DB look-up
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        if action == "watch":
            if realm_perm and not is_watching:
              if not res_exists:
                  wldict['error'] = True
                  if redirectback and not onwatchlistpage:
                    raise WatchlistError(
                        "Selected resource %s:%s doesn't exists!" % (realm,resid) )
                  redirectback = False
              else:
                  cursor.execute(
                      "INSERT INTO watchlist (wluser, realm, resid) "
                      "VALUES (%s,%s,%s);", (user, realm, resid) )
                  db.commit()
            if not onwatchlistpage and redirectback and msgrespage:
                  req.session['watchlist_message'] = (
                    'This %s has been added to your watchlist.' % realm)
            if self.gnotify and self.gnotifybydefault:
              action = "notifyon"
            else:
              if redirectback:
                req.redirect(reslink)
                raise RequestDone
              action = "view"
        elif action == "unwatch":
            if realm_perm:
              if ispattern:
                is_watching = True
                cursor.execute(
                    "DELETE FROM watchlist "
                    "WHERE wluser=%s AND realm=%s AND resid LIKE %s", (user,realm,pattern) )
                db.commit()
              elif is_watching:
                cursor.execute(
                    "DELETE FROM watchlist "
                    "WHERE wluser=%s AND realm=%s AND resid=%s;", (user, realm, resid))
                db.commit()
              elif not res_exists:
                wldict['error'] = True
                if redirectback and not onwatchlistpage:
                  raise WatchlistError(
                      "Selected resource %s:%s doesn't exists!" % (realm,resid) )
                redirectback = False
            if not onwatchlistpage and redirectback and msgrespage:
              req.session['watchlist_message'] = (
                'This %s has been removed from your watchlist.' % realm)
            if self.gnotify and self.gnotifybydefault:
              action = "notifyoff"
            else:
              if redirectback:
                req.redirect(reslink)
                raise RequestDone
              action = "view"

        if action == "notifyon":
            if self.gnotify:
              self.set_notify(req.session.sid, True, realm, resid)
              db.commit()
            if redirectback:
              if msgrespage:
                req.session['watchlist_notify_message'] = (
                  'You are now receiving '
                  'change notifications about this resource.')
              req.redirect(reslink)
              raise RequestDone
            action = "view"
        elif action == "notifyoff":
            if self.gnotify:
              self.unset_notify(req.session.sid, True, realm, resid)
              db.commit()
            if redirectback:
              if msgrespage:
                req.session['watchlist_notify_message'] = (
                  'You are no longer receiving '
                  'change notifications about this resource.')
              req.redirect(reslink)
              raise RequestDone
            action = "view"

        if action == "settings":
          d = args.copy()
          del d['action']
          self._save_user_settings(user, d)
          action = "view"
          wldict['user_settings'] = d
        else:
          wldict['user_settings'] = self._get_user_settings(user)

        wldict['is_watching'] = is_watching
        if action == "view":
            for (xrealm,handler) in self.realm_handler.iteritems():
              if handler.has_perm(req.perm):
                wldict[xrealm + 'list'] = handler.get_list(self, req)
                self.env.log.debug(xrealm + 'list: ' + str(wldict[xrealm + 'list']))
            return ("watchlist.html", wldict, "text/html")
        else:
            raise WatchlistError("Invalid watchlist action '%s'!" % action)

        raise WatchlistError("Watchlist: Unsupported request!")

    def has_watchlist(self, user):
        """Checks if user has a non-empty watchlist."""
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute(
            "SELECT count(*) FROM watchlist WHERE wluser=%s;", (user,)
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
        cursor.execute(
            "SELECT count(*) FROM watchlist WHERE realm=%s and resid=%s "
            "and wluser=%s;", (realm, to_unicode(resid), user)
        )
        count = cursor.fetchone()
        if not count or not count[0]:
            return False
        else:
            return True

    ### methods for IRequestFilter
    def post_process_request(self, req, template, data, content_type):
        msg = req.session.get('watchlist_message',[])
        if msg:
          add_notice(req, msg)
          del req.session['watchlist_message']
        msg = req.session.get('watchlist_notify_message',[])
        if msg:
          add_notice(req, msg)
          del req.session['watchlist_notify_message']

        # Extract realm and resid from path:
        parts = req.path_info[1:].split('/',1)

        # Handle special case for '/' and '/wiki'
        if len(parts) == 0 or not parts[0]:
            parts = ["wiki", "WikiStart"]
        elif len(parts) == 1:
            parts.append("WikiStart")

        realm, resid = parts[:2]

        if realm not in self.realms or not self.realm_handler[realm].has_perm(req.perm):
            return (template, data, content_type)

        href = Href(req.base_path)
        user = req.authname
        if user and user != "anonymous":
            if self.is_watching(realm, resid, user):
                add_ctxtnav(req, "Unwatch", href=href('watchlist', action='unwatch',
                    resid=resid, realm=realm), title="Remove %s from watchlist" % realm)
            else:
                add_ctxtnav(req, "Watch", href=href('watchlist', action='watch',
                    resid=resid, realm=realm), title="Add %s to watchlist" % realm)
            if self.gnotify and self.notifyctxtnav:
              if self.is_notify(req.session.sid, True, realm, resid):
                add_ctxtnav(req, "Do not Notify me", href=href('watchlist', action='notifyoff',
                    resid=resid, realm=realm), title="No not notify me if %s changes" % realm)
              else:
                add_ctxtnav(req, "Notify me", href=href('watchlist', action='notifyon',
                    resid=resid, realm=realm), title="Notify me if %s changes" % realm)

        return (template, data, content_type)


    def pre_process_request(self, req, handler):
        return handler

    # ITemplateProvider methods:
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('watchlist', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [ resource_filename(__name__, 'templates') ]


class WikiWatchlist(Component):
    implements( IWatchlistProvider )

    def get_realms(self):
      return ('wiki',)

    def get_realm_label(self, realm, plural=False):
      return plural and 'wikis' or 'wiki'

    def res_exists(self, realm, resid):
      return WikiPage(self.env, resid).exists

    def has_perm(self, perm):
      return 'WIKI_VIEW' in perm

    def get_list(self, wl, req):
      db = self.env.get_db_cnx()
      cursor = db.cursor()
      user = req.authname
      wikilist = []
      # Watched wikis which got deleted:
      cursor.execute(
          "SELECT resid FROM watchlist WHERE realm='wiki' AND wluser=%s "
          "AND resid NOT IN (SELECT DISTINCT name FROM wiki);", (user,) )

      for (name,) in cursor.fetchall():
          notify = False
          if wl.gnotify:
            notify = wl.is_notify(req.session.sid, True, 'wiki', name)
          wikilist.append({
              'name' : name,
              'author' : '?',
              'datetime' : '?',
              'comment' : tag.strong("DELETED!", class_='deleted'),
              'notify'  : notify,
              'deleted' : True,
          })
      # Existing watched wikis:
      cursor.execute(
          "SELECT name,author,time,version,comment FROM wiki AS w1 WHERE name IN "
          "(SELECT resid FROM watchlist WHERE wluser=%s AND realm='wiki') "
          "AND version=(SELECT MAX(version) FROM wiki AS w2 WHERE w1.name=w2.name) "
          "ORDER BY time DESC;", (user,) )

      wikis = cursor.fetchall()
      self.env.log.debug('user: ' + user)
      self.env.log.debug('wikis: ' + str(wikis))
      for name,author,time,version,comment in wikis:
          notify = False
          if wl.gnotify:
            notify = wl.is_notify(req.session.sid, True, 'wiki', name)
          wikilist.append({
              'name' : name,
              'author' : author,
              'version' : version,
              'datetime' : format_datetime( time ),
              'timedelta' : pretty_timedelta( time ),
              'timeline_link' : req.href.timeline(precision='seconds', from_=format_datetime (time,'iso8601')),
              'comment' : comment,
              'notify'  : notify,
          })
      return wikilist

class TicketWatchlist(Component):
    implements( IWatchlistProvider )

    def get_realms(self):
      return ('ticket',)

    def get_realm_label(self, realm, plural=False):
      return plural and 'tickets' or 'ticket'

    def res_exists(self, realm, resid):
      return Ticket(self.env, resid).exists

    def has_perm(self, perm):
      return 'TICKET_VIEW' in perm

    def get_list(self, wl, req):
      db = self.env.get_db_cnx()
      cursor = db.cursor()
      user = req.authname
      ticketlist = []
      cursor.execute(
          "SELECT id,type,time,changetime,summary,reporter FROM ticket WHERE id IN "
          "(SELECT CAST(resid AS decimal) FROM watchlist WHERE wluser=%s AND realm='ticket') "
          "GROUP BY id,type,time,changetime,summary,reporter "
          "ORDER BY changetime DESC;", (user,) )
      tickets = cursor.fetchall()
      for id,type,time,changetime,summary,reporter in tickets:
          self.commentnum = 0
          self.comment    = ''

          notify = False
          if wl.gnotify:
            notify = wl.is_notify(req.session.sid, True, 'ticket', id)

          cursor.execute(
              "SELECT author,field,oldvalue,newvalue FROM ticket_change "
              "WHERE ticket=%s and time=%s "
              "ORDER BY field DESC;",
              (id, changetime )
          )

          def format_change(field,oldvalue,newvalue):
              """Formats tickets changes."""
              fieldtag = tag.strong(field)
              if field == 'cc':
                  oldvalues = set(oldvalue and oldvalue.split(', ') or [])
                  newvalues = set(newvalue and newvalue.split(', ') or [])
                  added   = newvalues.difference(oldvalues)
                  removed = oldvalues.difference(newvalues)
                  strng = fieldtag
                  if added:
                      strng += tag(" ", tag.em(', '.join(added)), " added")
                  if removed:
                      if added:
                          strng += tag(', ')
                      strng += tag(" ", tag.em(', '.join(removed)), " removed")
                  return strng
              elif field == 'description':
                  return fieldtag + tag(" modified (", tag.a("diff",
                      href=href('ticket',id,action='diff',version=self.commentnum)), ")")
              elif field == 'comment':
                  self.commentnum = oldvalue
                  self.comment    = newvalue
                  return tag("")
              elif not oldvalue:
                  return fieldtag + tag(" ", tag.em(newvalue), " added")
              elif not newvalue:
                  return fieldtag + tag(" ", tag.em(oldvalue), " deleted")
              else:
                  return fieldtag + tag(" changed from ", tag.em(oldvalue),
                                        " to ", tag.em(newvalue))

          changes = []
          author  = reporter
          for author_,field,oldvalue,newvalue in cursor.fetchall():
              author = author_
              changes.extend( [format_change(field,oldvalue,newvalue), tag("; ") ])
          # changes holds list of formatted changes interleaved with
          # tag('; '). The first change is always the comment which
          # returns an empty tag, so we skip the first two elements
          # [tag(''), tag('; ')] and remove the last tag('; '):
          changes = changes and tag(changes[2:-1]) or tag()
          ticketlist.append({
              'id' : to_unicode(id),
              'type' : type,
              'author' : author,
              'commentnum': to_unicode(self.commentnum),
              'comment' : len(self.comment) <= 250 and self.comment or self.comment[:250] + '...',
              'datetime' : format_datetime( changetime ),
              'timedelta' : pretty_timedelta( changetime ),
              'timeline_link' : req.href.timeline(precision='seconds', from_=format_datetime (time,'iso8601')),
              'changes' : changes,
              'summary' : summary,
              'notify'  : notify,
          })
      return ticketlist

class ExampleWatchlist(Component):
    implements( IWatchlistProvider )

    def get_realms(self):
      return ('example',)

    def get_realm_label(self, realm, plural=False):
      return plural and 'examples' or 'example'

    def res_exists(self, realm, resid):
      return True

    def has_perm(self, perm):
      return True

    def get_list(self, wl, req):
      db = self.env.get_db_cnx()
      cursor = db.cursor()
      user = req.authname
      examplelist = []
      cursor.execute(
          "SELECT resid FROM watchlist WHERE wluser=%s AND realm='example'", (user,))
      examples = cursor.fetchall()
      for (name,) in examples:
        examplelist.append({'name':name})
      return examplelist

