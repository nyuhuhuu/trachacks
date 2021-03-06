from trac.ticket import ITicketChangeListener, Ticket
from trac.core import *

def save_custom_field_value( db, ticket_id, field, value ):
    cursor = db.cursor();
    cursor.execute("SELECT * FROM ticket_custom " 
                   "WHERE ticket=%s and name=%s", (ticket_id, field))
    if cursor.fetchone():
        cursor.execute("UPDATE ticket_custom SET value=%s "
                       "WHERE ticket=%s AND name=%s",
                       (value, ticket_id, field))
    else:
        cursor.execute("INSERT INTO ticket_custom (ticket,name,"
                       "value) VALUES(%s,%s,%s)",
                       (ticket_id, name, value))
        
def save_ticket_change( db, ticket_id, author, change_time, field, oldvalue, newvalue):
    cursor = db.cursor();
    cursor.execute("""SELECT * FROM ticket_change  
                   WHERE ticket=%s and author='%s' and time=%s and field='%s'"""%
                   (ticket_id, author, change_time, field))
    if cursor.fetchone():
        cursor.execute("""UPDATE ticket_change  SET oldvalue='%s', newvalue='%s' 
                       WHERE ticket=%s and author='%s' and time=%s and field='%s'"""%
                       (oldvalue, newvalue, ticket_id, author, change_time, field))
    else:
        cursor.execute("""INSERT INTO ticket_change  (ticket,time,author,field, oldvalue, newvalue) 
                        VALUES(%s, %s, '%s', '%s', '%s', '%s')"""%
                       (ticket_id, change_time, author, field, oldvalue, newvalue))

class TimeTrackingTicketObserver(Component):
    implements(ITicketChangeListener)
    def __init__(self):
        pass

    def watch_hours(self, ticket):
        def readTicketValue(name, tipe, default=0):
            if ticket.values.has_key(name):        
                return tipe(ticket.values[name] or default)
            else:
                cursor = self.env.get_db_cnx().cursor()
                cursor.execute("SELECT * FROM ticket_custom where ticket=%s and name='%s'" % (ticket.id, name))
                val = cursor.fetchone()
                if val:
                    return tipe(val[2] or default)
                return default

        hours = readTicketValue("hours", float)
        totalHours = readTicketValue("totalhours", float)
            
        if not hours == 0:
            self.log.debug("Starting to munge the hours")
            db = self.env.get_db_cnx()
            ticket_id = ticket.id
            cl = ticket.get_changelog()

            self.log.debug(dir(ticket))
            self.log.debug(cl)
            
            if cl:
                most_recent_change = cl[-1];
                change_time = most_recent_change[0]
                author = most_recent_change[1]
            else:
                change_time = ticket.time_created
                author = ticket.values["reporter"]
                
            newtotal = str(totalHours+hours)

            save_ticket_change( db, ticket_id, author, change_time, "totalhours", str(totalHours), newtotal)
            save_custom_field_value( db, ticket_id, "hours", '0')
            save_custom_field_value( db, ticket_id, "totalhours", newtotal )            

    def ticket_created(self, ticket):
        """Called when a ticket is created."""
        self.log.debug("About to act on the fact that a ticket was created")
        self.watch_hours(ticket)
                               

    def ticket_changed(self, ticket, comment, old_values):
        """Called when a ticket is modified.
        
        `old_values` is a dictionary containing the previous values of the
        fields that have changed.
        """
        self.watch_hours(ticket)

    def ticket_deleted(self, ticket):
        """Called when a ticket is deleted."""
