"""
Test sqlite database wrapper
"""

import pytest
import os
import sqlite3
import tempfile

TEST_DB_SIMPLE = (
    """CREATE TABLE test ( key integer primary key )""",
)

def test_sqlite_create_database_relative_filename(tmpdir):
    """Create simple database

    """
    from systematic.sqlite import SQLiteDatabase

    # DB without path: create empty database to current directory. Remove afterwards
    tmpfile = tempfile.NamedTemporaryFile(suffix='.sqlite', prefix='unittests', dir=os.getcwd())
    filename = os.path.basename(tmpfile.name)
    db = SQLiteDatabase(filename)
    assert os.path.isfile(filename)
    os.unlink(filename)

def test_sqlite_create_database_with_path(tmpdir):
    """Create simple database

    """
    from systematic.sqlite import SQLiteDatabase

    # DB with path: Create empty test database
    filename = '{0}/createdb_empty.sqlite'.format(tmpdir)
    db = SQLiteDatabase(filename)
    assert os.path.isfile(filename)

def test_sqlite_operations(tmpdir):
    """Basic sqlite operations

    Create trivial database with tables_sql argument, test basic operations
    """
    from systematic.sqlite import SQLiteDatabase

    # DB with tables: Create database with one table
    filename = '{0}/createdb_simple.sqlite'.format(tmpdir)
    db = SQLiteDatabase(filename, TEST_DB_SIMPLE)
    assert os.path.isfile(filename)

    c = db.cursor
    c.execute("""SELECT * FROM test""")
    c.fetchall()

    c = db.cursor
    c.execute("""DROP TABLE test""")

    with pytest.raises(sqlite3.OperationalError):
        c = db.cursor
        c.execute("""SELECT * FROM test""")
        c.fetchall()
