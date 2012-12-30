"""
Common abstraction class for sqlite databases
"""

import os,sqlite3

from systematic.log import Logger,LoggerError

class SQLiteError(Exception):
    """
    Exception raised by SQLiteDatabase errors.
    """
    def __str__(self):
        return self.args[0]

class SQLiteDatabase(object):
    """
    Singleton instance sqlite3 file access wrapper
    """
    def __init__(self,db_path,tables_sql=None,foreign_keys=True):
        """
        Opens given database reference. If tables_sql list is given,
        each SQL command in the list is executed to initialize the
        database.
        """
        self.log = Logger('sqlite').default_stream
        self.db_path = db_path

        if db_path is None:
            raise SQLiteError('Database path is None')
        db_dir = os.path.dirname(db_path)
        if not os.path.isdir(db_dir):
            try:
                os.makedirs(db_dir)
            except IOError,(ecode,emsg):
                raise SQLiteError('Error creating directory %s: %s' % (db_dir,emsg))

        self.conn = sqlite3.Connection(self.db_path)

        c = self.cursor
        if foreign_keys:
            c.execute('PRAGMA foreign_keys=ON')
            c.fetchone()

        if tables_sql:
            for q in tables_sql:
                try:
                    c.execute(q)
                except sqlite3.OperationalError,emsg:
                    raise SQLiteError('Error executing SQL:\n%s\n%s' % (q,emsg))

    def __del__(self):
        """
        Closes the database reference
        """
        if hasattr(self,'conn') and self.conn is not None:
            self.conn.close()
            self.conn = None

    def __result2dict__(self,*args,**kwargs):
        """
        Compatibility method for old API for as_dict()
        """
        return self.as_dict(*args,**kwargs)

    @property
    def cursor(self):
        c  self.conn.cursor()
        if c is None:
            raise SQLiteError('Could not get cursor to database')
        return c

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

    def as_dict(self,cursor,result):
        """
        Return a query result from sqlite as dictionary based on cursor
        field descriptions.
        """
        data = {}
        for i,k in enumerate([e[0] for e in cursor.description]):
            data[k] = result[i]
        return data
