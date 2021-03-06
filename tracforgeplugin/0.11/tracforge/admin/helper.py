# Created by Noah Kantrowitz on 2008-02-19.
# Copyright (c) 2008 Noah Kantrowitz. All rights reserved.
import sys

import pkg_resources
pkg_resources.require('Trac')

from trac.env import open_environment

from tracforge.admin.model import Prototype

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    
    # Load initial parameters from the command-line
    master_path = argv[0]
    prototype_name = argv[1]
    data = {
        'name': argv[2],
        'full_name': argv[3],
    }
    
    # Load master env and the prototype
    env = open_environment(master_path)
    prototype = Prototype(env, prototype_name)
    
    # Run the prototype and add the project to the master table
    prototype.execute(data)
    db = env.get_db_cnx()
    cursor = db.cursor()
    cursor.execute('INSERT INTO tracforge_projects (name, env_path) VALUES (%s, %s)',
                   (data['name'], data['env'].path))
    db.commit()
    

if __name__ == '__main__':
    sys.exit(main())