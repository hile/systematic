"""
Unit tests for sqlite wrapper
"""

import os
import sys
import sqlite3
import unittest

from systematic.sqlite import SQLiteDatabase, SQLiteError

test_data_path = os.path.join(os.sep.join(os.path.realpath(__file__).split(os.sep)[:-1]), 'data')

class test_sqlite(unittest.TestCase):

    def test_create_new_database_without_foreign_keys_pragma(self):
        test_db_path = os.path.join(test_data_path, 'test_no_foreign_keys.sqlite')
        if os.path.isfile(test_db_path):
            os.unlink(test_db_path)
        db = SQLiteDatabase(test_db_path, foreign_keys=False)
        del db
        self.assertTrue(os.path.isfile(test_db_path))

    def test_create_new_database_with_foreign_keys_pragma(self):
        test_db_path = os.path.join(test_data_path, 'test_foreign_keys.sqlite')
        if os.path.isfile(test_db_path):
            os.unlink(test_db_path)
        db = SQLiteDatabase(test_db_path, foreign_keys=True)
        del db
        self.assertTrue(os.path.isfile(test_db_path))

    def test_create_new_database_with_sql_no_foreign_keys(self):
        test_db_path = os.path.join(test_data_path, 'test_no_foreign_keys.sqlite')
        test_sql = [
            """CREATE TABLE test ( id INT PRIMARY KEY, name TEXT );""",
            """CREATE TABLE IF NOT EXISTS testref ( id INT PRIMARY KEY, test INT, FOREIGN KEY (test) REFERENCES test(id) );""",
            """INSERT INTO test (id,name) VALUES (2,"test1")""",
            """INSERT INTO testref (id,test) VALUES (1,2)""",
        ]
        if os.path.isfile(test_db_path):
            os.unlink(test_db_path)
        db = SQLiteDatabase(test_db_path, tables_sql=test_sql, foreign_keys=False)

        c = db.cursor
        with self.assertRaises(sqlite3.IntegrityError):
            c.execute("""INSERT INTO testref (id, test) VALUES (1, 3)""")

        # Must no raise exception
        c.execute("""INSERT INTO testref (id, test) VALUES (123, 223)""")

        c.execute("""SELECT id, name FROM test WHERE name="test1" """)
        res = c.fetchone()
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(db.as_dict(c, res), dict)

        del db
        self.assertTrue(os.path.isfile(test_db_path))
        os.unlink(test_db_path)

    def test_create_new_database_with_sql_with_foreign_keys(self):
        test_db_path = os.path.join(test_data_path, 'test_no_foreign_keys.sqlite')
        test_sql = [
            """CREATE TABLE test ( id INT PRIMARY KEY,  name TEXT );""",
            """CREATE TABLE IF NOT EXISTS testref ( id INT PRIMARY KEY, test TEXT, FOREIGN KEY (test) REFERENCES test(id) );""",
            """INSERT INTO test (id, name) VALUES (2, "test1")""",
            """INSERT INTO testref (id, test) VALUES (1, 2)""",
        ]
        if os.path.isfile(test_db_path):
            os.unlink(test_db_path)
        db = SQLiteDatabase(test_db_path, tables_sql=test_sql, foreign_keys=True)

        c = db.cursor
        with self.assertRaises(sqlite3.IntegrityError):
            c.execute("""INSERT INTO testref (id, test) VALUES (1, 3)""")

        # Must raise exception
        with self.assertRaises(sqlite3.IntegrityError):
            c.execute("""INSERT INTO testref (id, test) VALUES (123, 223)""")

        c.execute("""SELECT id, name FROM test WHERE name="test1" """)
        res = c.fetchone()
        self.assertIsInstance(res, tuple)
        self.assertIsInstance(db.as_dict(c, res),dict)

        del db
        self.assertTrue(os.path.isfile(test_db_path))
        os.unlink(test_db_path)





