# -*- coding:utf8 -*-
import re, os, codecs
import urllib 
from time import time
from threading import Lock
from tempfile import mktemp, NamedTemporaryFile
from subprocess import Popen, PIPE


from trac.core import *
from trac.config import Option
from trac.wiki import IWikiMacroProvider
from trac.web import IRequestHandler 
from trac.wiki.formatter import system_message

from genshi.builder import tag

from cache import Cache

try:
    import hashlib
    make_hash = hashlib.sha1
except ImportError:
    import sha
    make_hash = sha.sha

help_template = u"""
Render %(diagtype)s diagrams. 
See [http://tk0miya.bitbucket.org/%(cmdname)s/build/html/index.html %(cmdname)s]
 Example::
{{{
{{{
#!%(cmdname)s(type=svg, width=600)
%(example)s
}}}
}}}
 Arguments (Only Trac 0.12 or later)::
 * '''type''' -- Image format(svg or png).[[BR]]
   In Trac 0.11, you can use %(cmdname)s_svg/%(cmdname)s_png processors instead.
 * '''others(width, height, align etc)''' -- Treated as IMG tag attributes.

"""

blockdiag_example = \
"""{
  A -> B -> C
       B -> D    
}"""

seqdiag_example = \
"""{
  browser  -> webserver [label = "GET /index.html"];
  browser <-- webserver;
  browser  -> webserver [label = "POST /blog/comment"];
              webserver  -> database [label = "INSERT comment"];
              webserver <-- database;
  browser <-- webserver;
}""" 

actdiag_example = \
"""{
  A -> B -> C -> D;
  lane foo {
    A; B;
  }
  lane bar {
    C; D;
  }
}"""

nwdiag_example = \
"""{
  network dmz {
    web01;
    web02;
    stg01;
  }
  network internal {
    web01;
    web02;
    db01;
  }
}"""

def get_help(**kwargs):
    return help_template % kwargs

macro_defs = {  "blockdiag" : get_help(cmdname="blockdiag", diagtype="block", example=blockdiag_example), 
                "seqdiag" : get_help(cmdname="seqdiag", diagtype="sequence", example=seqdiag_example), 
                "actdiag" : get_help(cmdname="actdiag", diagtype="activity", example=actdiag_example), 
                "nwdiag" : get_help(cmdname="nwdiag", diagtype="network", example=nwdiag_example), 
              }
for cmd in macro_defs.keys():
    for type in ('svg', 'png'):
        macro_defs['%s_%s' % (cmd, type)] = 'Alternate of %s(type=%s) for Trac 0.11' % (cmd, type)
        
        
class ImageGenerationError(Exception):
    pass

class BlockDiagPlugin(Component):
    """
    Provide blockdiag/seqdiag/actdiag/nwdiag processor witch embed diagrams generated by blockdiag family.
    See http://tk0miya.bitbucket.org/blockdiag/build/html/index.html and http://tk0miya.bitbucket.org/seqdiag/build/html/index.html
        http://tk0miya.bitbucket.org/actdiag/build/html/index.html and http://tk0miya.bitbucket.org/nwdiag/build/html/index.html
    """
    implements (IWikiMacroProvider, IRequestHandler)

    _default_type = Option('blockdiag', 'default_type', 'png',
        doc="Default output format type which will be used when the type "
            "isn't given.")

    _font = Option('blockdiag', 'font', '',
        doc="Path to a font file to draw a diagram.")
    
    macros = None

    content_types = {
            "png" : "image/png",
            "svg" : "image/svg+xml",
            }
    
    def __init__(self):
        self.cache = Cache(self.env)

    def get_macros(self):
        return macro_defs.keys()

    def get_macro_description(self, name):
        return macro_defs[name]

    def expand_macro(self, formatter, name, content, args = None):
        if args is None:
            args = {}

        if name[-4:] in ('_svg', '_png'):
            name, type = name.split('_')
        else:
            type = (args.get('type') or self._default_type).lower()
            if type not in ('svg', 'png'):
                return system_message("Invalid type(%s). Type must be 'svg' or 'png'" % type)
                
        font = self._font

        # nonascii unicode can't be passed to hashlib.
        id = make_hash('%s,%s,%s,%r' % (name, type, font, content)).hexdigest()

        ## Create img tag.
        params = { "src": formatter.req.href("%s/%s.%s" % (name, id, type)) }
        for key, value in args.iteritems():
            if key != "type":
                params[key] = value
        output = tag.img(**params)

        ## Generate image and cache it.
        def generate_image():
            infile = mktemp(prefix='%s-' % name)
            outfile = mktemp(prefix='%s-' % name)
            try:
                try:
                    f = codecs.open(infile, 'w', 'utf8')
                    try:
                        f.write(content)
                    finally:
                        f.close()
                    cmd = [name, '-a', '-T', type, '-o', outfile, infile]
                    if font:
                        cmd.extend(['-f', font])
                    self.env.log.debug('(%s) command: %r' % (name, cmd))
                    try:
                        proc = Popen(cmd, stderr=PIPE)
                        stderr_value = proc.communicate()[1]
                    except Exception, e:
                        self.env.log.error('(%s) %r' % (name, e))
                        raise ImageGenerationError("Failed to generate diagram. (%s is not found.)" % name)
    
                    if proc.returncode != 0 or not os.path.isfile(outfile):
                        self.env.log.error('(%s) %s' % (name, stderr_value))
                        raise ImageGenerationError("Failed to generate diagram. (rc=%d)" % proc.returncode)
                    f = open(outfile, 'rb')
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    return data
                except ImageGenerationError:
                    raise
                except Exception, e:
                    self.env.log.error('(%s) %r' % (name, e))
                    raise ImageGenerationError("Failed to generate diagram.")
            finally:
                for path in (infile, outfile):
                    try:
                        os.remove(path)
                    except:
                        pass
                    
        try:
            self.cache.cache(id, type, generate_image)
        except ImageGenerationError, e:
            return system_message(str(e))
            
        return output

    def match_request(self, req):
        return re.match(r'/([a-z]+diag)/.+$', req.path_info)

    def process_request(self, req):
        m = re.match(r'/([a-z]+diag)/(.+)\.(png|svg)$', req.path_info)
        if not m:
            return ""
        id, type = m.group(2), m.group(3)
        data = self.cache.get(id, type)
        if data:
            req.send(data, self.content_types[type], status=200)
        else:
            self.env.log.error('(blockdiag) data not found by %s, %s' % (id, type))
            
        return ""
