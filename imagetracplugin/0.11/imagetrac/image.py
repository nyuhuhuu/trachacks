"""
ImageTrac:
a plugin for Trac to add images to tickets upon creaton
http://trac.edgewall.org
"""

from cStringIO import StringIO
from cropresize import crop_resize
from trac.attachment import Attachment
from trac.attachment import IAttachmentChangeListener
from trac.config import BoolOption
from trac.config import ListOption
from trac.config import Option
from trac.core import *
from trac.mimeview import Mimeview
from trac.ticket import Ticket
from trac.ticket.api import ITicketChangeListener
from trac.ticket.api import ITicketManipulator
from trac.web.api import IRequestFilter
from PIL import Image

class ImageTrac(Component):

    implements(ITicketManipulator, 
               ITicketChangeListener, 
               IRequestFilter, 
               IAttachmentChangeListener)

    mandatory_image = BoolOption('ticket-image', 'mandatory_image', 'false', 
                                 "Enforce a mandatory image for created tickets")
    thumbnail = Option('ticket-image', 'size.thumbnail', '32x32',
                       "size of the ticket thumbnail image")
    default_size = Option('ticket-image', 'size.default', '488x',
                          "size of the ticket default image")


    ### methods for ITicketManipulator

    """Miscellaneous manipulation of ticket workflow features."""

    def prepare_ticket(self, req, ticket, fields, actions):
        """Not currently called, but should be provided for future
        compatibility."""

    def validate_ticket(self, req, ticket):
        """Validate a ticket after it's been populated from user input.
        
        Must return a list of `(field, message)` tuples, one for each problem
        detected. `field` can be `None` to indicate an overall problem with the
        ticket. Therefore, a return value of `[]` means everything is OK."""
        image = req.args.get('ticket_image')

        if hasattr(image, 'fp'):
            mimeview = Mimeview(self.env)
            mimetype = mimeview.get_mimetype(image.filename)
            if mimetype is None:
                return[('ticket_image', 'Uploaded file is not an image')]
            if mimetype.split('/',1)[0] != 'image':
                return [('ticket_image', 'Uploaded file is not an image, instead it is %s' % mimetype)]
            
            try:
                Image.open(image.file)
            except IOError, e:
                return[('ticket_image', str(e))]

            # store the image temporarily for new tickets
            if ticket.exists:
                self.attach(ticket, image)
            else:
                if not hasattr(self, 'image'):
                    self.image = {}
                self.image[ticket['summary']] = req.args['ticket_image']

        else:
            if not ticket.exists and self.mandatory_image:
                return [('ticket_image', 'Images required for tickets. Please upload an image.')]


        return []

    ### methods for ITicketChangeListener

    """Extension point interface for components that require notification
    when tickets are created, modified, or deleted."""

    def ticket_changed(self, ticket, comment, author, old_values):
        """Called when a ticket is modified.
        
        `old_values` is a dictionary containing the previous values of the
        fields that have changed.
        """

    def ticket_created(self, ticket):
        """Called when a ticket is created."""
        if not hasattr(self, 'image'):
            return 
        image = self.image.pop(ticket['summary'], None)
        if image is None:
            return 

        self.attach(ticket, image)            

    def ticket_deleted(self, ticket):
        """Called when a ticket is deleted."""
        

    ### methods for IRequestFilter

    """Extension point interface for components that want to filter HTTP
    requests, before and/or after they are processed by the main handler."""

    def post_process_request(self, req, template, data, content_type):
        """Do any post-processing the request might need; typically adding
        values to the template `data` dictionary, or changing template or
        mime type.
        
        `data` may be update in place.

        Always returns a tuple of (template, data, content_type), even if
        unchanged.

        Note that `template`, `data`, `content_type` will be `None` if:
         - called when processing an error page
         - the default request handler did not return any result

        (Since 0.11)
        """

        if template == 'ticket.html':
            ticket = data['ticket']
            data['images'] = self.images(ticket, req.href)
                        
        return (template, data, content_type)

    def pre_process_request(self, req, handler):
        """Called after initial handler selection, and can be used to change
        the selected handler or redirect request.
        
        Always returns the request handler, even if unchanged.
        """
        return handler

    ### methods for IAttachmentChangeListener

    """Extension point interface for components that require notification when
    attachments are created or deleted."""

    def attachment_added(self, attachment):
        """Called when an attachment is added."""
        if attachment.resource.parent.realm == 'ticket':
            try:
                filename, category = self.image_category(attachment)
            except TypeError:
                return
            if category == 'original':
                ticket = Ticket(self.env, attachment.resource.parent.id)
                self.create_sizes(ticket, attachment)

    def attachment_deleted(self, attachment):
        """Called when an attachment is deleted."""
        # XXX should delete the default from the DB 
        # if the attachment deleted is the default
    
    ### internal methods

    def attach(self, ticket, image):
        attachment = Attachment(self.env, 'ticket', ticket.id)
        attachment.author = ticket['reporter']
        attachment.description = ticket['summary']
        image.file.seek(0,2) # seek to end of file
        size = image.file.tell()
        filename = image.filename
        image.file.seek(0)
        attachment.insert(filename, image.file, size)

        # XXX shouldn't this only be called for, like, the
        # first image or whenever you really want to set the default?
        from imagetrac.default_image import DefaultTicketImage
        if self.env.is_component_enabled(DefaultTicketImage):
            DefaultTicketImage(self.env).set_default(ticket.id, filename)
        # create_sizes will be called as a function of
        # IAttachmentChangeListener

    def create_sizes(self, ticket, attachment):
        """create the sizes for a ticket image"""

        filename = attachment.filename

        # add the specified sizes as attachments
        sizes = self.sizes()
        for name, size in sizes.items():
            # crop the image
            image = Image.open(attachment.path)
            i = crop_resize(image, size)
            buffer = StringIO()
            i.save(buffer, image.format)
            buffer.seek(0,2) # seek to end of file
            filesize = buffer.tell()
            buffer.seek(0)
            a = Attachment(self.env, 'ticket', ticket.id)
            a.author = ticket['reporter']
            a.description = ticket['summary']
            f = ('.%sx%s.' % (size[0] or '', size[1] or '')).join(filename.rsplit('.', 1)) # XXX assumes the file has an extension
            a.insert(f, buffer, filesize)


    def images(self, ticket, href=None):
        """returns images for a ticket"""

        # construct a ticket from an id
        if isinstance(ticket, int):
            ticket = Ticket(self.env, ticket)

        if not ticket.exists:
            return {}
        
        attachments = list(Attachment.select(self.env, 'ticket', ticket.id))
        images = {}
        for attachment in attachments:
            try:
                filename, category = self.image_category(attachment)
            except TypeError:
                continue
            images.setdefault(filename, {})[category] = attachment.filename

        if href is not None:
            # turn the keys into links
            for values in images.values():
                for key, value in values.items():
                    values[key] = href('attachment', 'ticket', ticket.id, value, format='raw')
        return images

    def image_category(self, attachment):
        reverse_sizes = dict([(value, key) for key, value in self.sizes().items()])
        mimeview = Mimeview(self.env)
        mimetype = mimeview.get_mimetype(attachment.filename)
        if mimetype and mimetype.split('/',1)[0] != 'image':
            return None
        filename = attachment.filename
        try:
            size = Image.open(attachment.path).size
        except IOError:
            return None
        for _size in reverse_sizes:
            parts = filename.rsplit('.', 2)
            if len(parts) == 3:
                dimension = '%sx%s' % (_size[0] or '', _size[1] or '')
                if parts[-2] == dimension:
                    filename = '%s.%s' % (parts[0], parts[-1])
                    return (filename, reverse_sizes[_size])

        return (filename, 'original')

        
    def sizes(self):
        """return image sizes"""
        sizes = { 'default': self.default_size,
                  'thumbnail': self.thumbnail }
        for option, value in self.env.config.options('ticket-image'):
            if option.startswith('size.'):
                sizes[option.split('.', 1)[-1]] = value

        for size in sizes:
            try:
                dimension = [ i.strip() and int(i) or None for i in sizes[size].split('x') ]
            except ValueError:
                sizes.pop(size)
                continue
            sizes[size] = tuple(dimension)
        return sizes
