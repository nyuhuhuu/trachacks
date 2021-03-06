# -*- coding: utf-8 -*-

from trac.core import *
from trac.env import IEnvironmentSetupParticipant
from trac.db import Table, Column, Index


class BlogPartsProvider(Component):
    implements(IEnvironmentSetupParticipant)

    SCHEMA = [
        Table('blogpart', key = ('name'))[
              Column('name'),
              Column('summery'),
              Column('description'),
              Column('header'),
              Column('body'),
              Column('argnum'),
              Column('time'),
              ]
        ]

    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        self._upgrade_db(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        cursor = db.cursor()
        #if self._need_migration(db):
        #    return True
        try:
            cursor.execute("select count(*) from blogpart")
            cursor.fetchone()
            return False
        except:
            db.rollback()
            return True

    def upgrade_environment(self, db):
        self._upgrade_db(db)
        
    def _upgrade_db(self, db):
        try:
            try:
                from trac.db import DatabaseManager
                db_backend, _ = DatabaseManager(self.env)._get_connector()
            except ImportError:
                db_backend = self.env.get_db_cnx()

            cursor = db.cursor()
            for table in self.SCHEMA:
                for stmt in db_backend.to_sql(table):
                    self.env.log.debug(stmt)
                    cursor.execute(stmt)
            db.commit()

            # Migrate old data
            #if self._need_migration(db):
            #    cursor = db.cursor()
            #    cursor.execute("INSERT INTO tags (tagspace, name, tag) SELECT "
            #                   "'wiki', name, namespace FROM wiki_namespace")
            #    cursor.execute("DROP TABLE wiki_namespace")
            #    db.commit()
        except:
            db.rollback()
            raise
