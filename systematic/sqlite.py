"""
Common abstraction class for sqlite databases
"""

import os,sqlite3,logging

class SQLiteError(Exception):
    """
    Exception raised by SQLiteDatabase errors.
    """
    def __str__(self):
        return self.args[0]

class SQLiteDatabase(object):
    """
    Parent class to simplify access to sqlite databases from python 
    """
    def __init__(self,db_path,tables_sql=None):
        """
        Opens given database reference. If tables_sql list is given, 
        each SQL command in the list is executed to initialize the
        database.
        """ 
        self.db_path = db_path
        self.log = logging.getLogger('modules')

        db_dir = os.path.dirname(db_path)
        if not os.path.isdir(db_dir):
            try:
                os.makedirs(db_dir)
            except IOError,(ecode,emsg):
                raise SQLiteError(
                    'Error creating directory %s: %s' % (db_dir,emsg)
                )

        #self.log.debug('Opening database: %s' % self.db_path)
        self.conn = sqlite3.Connection(self.db_path)
        if tables_sql:
            c = self.cursor
            for q in tables_sql:
                c.execute(q)
            del c

    def __del__(self):
        """
        Closes the database reference
        """
        #self.log.debug('Closing database: %s' % self.db_path)
        self.conn.close()
        self.conn = None

    def __getattr__(self,attr):
        """
        Accessor for dynamic attributes:
        cursor      Returns new connection cursor
        """
        if attr == 'cursor':
            return self.conn.cursor()
        raise AttributeError('No such SQLiteDatabase attribute: %s' %  attr)

    def __result2dict__(self,cursor,result):
        """
        Return a query result from sqlite as dictionary based on cursor
        field descriptions.
        """
        data = {}
        for i,k in enumerate([e[0] for e in cursor.description]):
            data[k] = result[i] 
        return data

    def rollback(self):
        """
        Rollback transaction
        """
        return self.conn.rollback()

    def commit(self):
        """
        Commit transaction
        """
        return self.conn.commit()

