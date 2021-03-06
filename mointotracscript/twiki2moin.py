#!/usr/bin/python
import os
import re
import shutil

def main(old_dir, new_dir, data_dir=None):
    names = os.listdir(old_dir)
    names.sort()
    for name in names:
        if name[-4:] == ".txt":
            topic = name[:-4]
            print topic

            txt = file(os.path.join(old_dir, name)).read()
            makePage(new_dir, topic, twiki2moin(txt))
            if data_dir:
                copyAttachments(new_dir, data_dir, topic, txt)

def twiki2moin(txt):
    # remove lines starting and ending with %
    txt = re.compile("^%.*%$", re.M).sub("", txt)
    # change attachment links
    txt = re.compile(r"\[\[%ATTACHURL%/(.*?)\]\[(.*?)\]\]").sub('[attachment:\\1 \\2]', txt)
    # change links
    txt = re.compile(r"\[\[(https?://[^\[\]]+)\]\[(.*?)\]\]").sub('[\\1 \\2]', txt)
    txt = re.compile(r"\[\[(.*?)\]\[(.*?)\]\]").sub('[:\\1:\\2]', txt)
    txt = re.compile(r"\[\[(.*?)\]\]").sub('["\\1"]', txt)
    # convert bold italic
    txt = re.compile(r"\b__([^*\n]*?)__").sub("'''''\\1'''''", txt)
    # convert italic
    txt = re.compile(r"\b_([^*\n]*?)_").sub("''\\1''", txt)
    # convert bold
    txt = re.compile(r"\*\b([^*\n]*?)\*").sub("'''\\1'''", txt)
    # convert verbatim
    txt = re.compile(r"\B=\b([^*\n]*?)=\B").sub("{{{\\1}}}", txt)
    txt = re.compile(r"<verbatim>").sub("{{{", txt)
    txt = re.compile(r"</verbatim>").sub("}}}", txt)
    txt = re.compile(r"<pre>").sub("{{{", txt)
    txt = re.compile(r"</pre>").sub("}}}", txt)
    # convert bold fix .. no equivalent
    txt = re.compile(r"\B==\b([^*\n]*?)==\B").sub("{{{\\1}}}", txt)
    
    # convert definition list 
    # Three spaces, a dollar sign, the term, a colon, a space, followed by the definition ( "   $ term: definition" -> "term:: definition" )
    txt = re.compile("   \$ (.*): (.*)").sub(" \\1:: \\2", txt)
    # convert lists
    txt = re.compile("((?: {3})+)([0-9]+)\s(.*)").sub("\\1\\2. \\3", txt)
    txt = re.compile("(\t+)([0-9]+)\s(.*)").sub("\\1\\2. \\3", txt)
    
    # convert headings
    txt = re.compile("^-?" + re.escape("---+++++") + "\s*(.*)$", re.M).sub("====== \\1 ======", txt)
    txt = re.compile("^-?" + re.escape("---++++") + "\s*(.*)$", re.M).sub("===== \\1 =====", txt)
    txt = re.compile("^-?" + re.escape("---+++") + "\s*(.*)$", re.M).sub("==== \\1 ====", txt)
    txt = re.compile("^-?" + re.escape("---++") + "\s*(.*)$", re.M).sub("=== \\1 ===", txt)
    txt = re.compile("^-?" + re.escape("---+") + "\s*(.*)$", re.M).sub("== \\1 ==", txt)
    txt = re.compile("^-?" + re.escape("---#") + "\s*(.*)$", re.M).sub("= \\1 =", txt)
    # remove signatures
    ## uncommento to enable ## txt = re.compile("^-- Main.([a-z]+) - [0-9]+ [a-zA-Z]+ 200[0-9]\s*\n?", re.M).sub("", txt)
    # tables
    txt = re.compile(r"\|", re.M).sub("||", txt)
    # rules
    txt = re.compile(r"^\s*<hr ?/?>\s*$", re.M).sub("----", txt)
    return txt

def makePage(new_dir, topic, txt):
    txt = unicode(txt, "latin1").encode("utf8")
    name = os.path.join(new_dir, topic)
    try:
        os.mkdir(name)
    except OSError:
        pass
    try:
        os.mkdir(os.path.join(name,"revisions"))
    except OSError:
        pass
    file(os.path.join(name,"current"), "w").write("00000001")
    file(os.path.join(name,"revisions","00000001"), "w").write(txt)

def copyAttachments(new_dir, data_dir, topic, txt):
    name = os.path.join(new_dir,topic)
    try:
        os.mkdir(name)
    except OSError:
        pass
    try:
        os.mkdir(os.path.join(name,"attachments"))
    except OSError:
        pass
    attachments = re.compile("%META:FILEATTACHMENT.*name=\"(.*?)\"\s",
        re.M).findall(txt)
    for attachment in attachments:
        try:
            shutil.copyfile(
                os.path.join(data_dir,topic,attachment),
                os.path.join(name,"attachments",attachment))
        except IOError:
            print "Could not copy attachment %s for topic %s" \
                % (attachment, topic)
            pass


twikidir = "/var/lib/twiki/data/Main"
twikidata = "/var/lib/twiki/pub/Main"
moinout   = "moin"
quiet = False

def defaults():
    print "current defaults:"
    print "   --twiki=%s --data=%s -o=%s" %(twikidir, twikidata, moinout)
def usage():
    print "usage twiki2moin [-ho] [--twiki=<twiki pages>][--data=<twiki data>]"
    print "   -h    print help"
    print "   -o    output dir"
    print "   -q    quiet run"
    defaults()

if __name__ == '__main__':
    import sys, getopt
    quiet = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hoq:", ["twiki", "data"])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    for o, a in opts:
        if o=="-h":
            usage()
            sys.exit(0)
        elif o=="-o":
            moinout = a
        elif o=="--twiki":
            twikidir = a
        elif o=="--data":
            twikidata = a

    if not quiet:
        defaults()
        
    main(twikidir, moinout, twikidata )
