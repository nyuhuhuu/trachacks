from trac.env import open_environment
from trac.db import Table, Column, Index

class DownloaderDB:
    
    ##
    ## Downloader plug-in's database schema
    ##
    
    schema = [
        # Downloader
        Table('downloader_category', key='id')[
            Column('id', auto_increment=True),
            Column('name'),
            Column('notes'),
            Column('sort', type='int'),
            Column('timestamp', type='int'),
            Column('deleted', type='int')],
        Table('downloader_release', key=('id'))[
            Column('id', auto_increment=True),
            Column('category'),
            Column('name'),
            Column('notes'),
            Column('sort', type='int'),
            Column('timestamp', type='int'),
            Column('deleted', type='int')],
        Table('downloader_file', key=('id'))[
            Column('id', auto_increment=True),
            Column('release'),
            Column('name'),
            Column('notes'),
            Column('architecture'),
            Column('sort', type='int'),
            Column('timestamp', type='int'),
            Column('deleted', type='int')],
        Table('downloader_downloaded', key=('id'))[
            Column('id', auto_increment=True),
            Column('file', type='int'),
            Column('timestamp', type='int')],
        Table('downloader_downloaded_attributes', key=(['downloaded', 'name']))[
            Column('downloaded', type='int'),
            Column('name'),
            Column('value')],
    ]
    
    def __init__(self, env=None):
        if not env:
            self.env = open_environment()
        else:
            self.env = env
        
        self._init_db()
    
    def _init_db(self):
        """Create tables for Downloader plug-in if they doesn't exist."""
        db = self.env.get_db_cnx()
        
        cursor = db.cursor()
        if not self._downloader_db_exists(cursor):
            for table in self.schema:
                for stmt in db.cnx.to_sql(table):
                    cursor.execute(stmt)
            self.env.log.info("Downloader plug-in DB was created.")
                
    def _downloader_db_exists(self, cursor):
        """
        Checks existence of Downloader plug-in's DB.
        NOTE that it checks only existence of the first table!
        """
        try:
            cursor.execute("SELECT 1 FROM downloader_category")
        except:
            self.env.log.info("Downloader plug-in DB does not exist.")
            return False
        
        return True