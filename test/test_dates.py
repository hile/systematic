"""
Unit tests for dates parsers
"""

import sys,unittest,time
from datetime import datetime,date

from systematic.dates import Day,Week,Month,DatesError

VALID_DATE_FORMATS = (
    ('2012-02-29', None),
    ('2012-02-28', '%Y-%m-%d'),
    ('1.2.2012', '%d.%m.%Y'),
    (long(time.mktime(time.localtime())), None),
    (time.mktime(time.localtime()), None),
    (time.localtime(), None),
    (datetime.now(), None),
    (date(*time.localtime()[:3]), None),
    ('', None),
)

INVALID_DATE_FORMATS = (
    ('1024-13-13', None),
    ('2013-02-29', None),
    ('abcd', None),
    ('', '')
)

class test_dates(unittest.TestCase):

    def test_day_arguments(self):
        for value, date_format in VALID_DATE_FORMATS:
            try:
                Day(value=value, input_format=date_format)
            except DatesError, emsg:
                raise AssertionError('format {0}: {1}'.format(date_format, emsg))

        for value, date_format in INVALID_DATE_FORMATS:
            with self.assertRaisesRegexp(DatesError, 'Error parsing date: {0}'.format(value)):
                Day(value=value, input_format=date_format)

    def test_week_operators(self):
        self.assertEquals(len(list(Week())), 7)

        previous = Week('2012-01-05')-1
        self.assertEquals(previous.first.year, 2011)
        self.assertEquals(previous.first.weekday, 1)
        self.assertEquals(previous.last.year, 2012)
        self.assertEquals(previous.last.weekday, 7)

        next = Week('2011-02-25')+1
        self.assertEquals(next.last.month, 3)
        self.assertEquals(next.last.weekday, 7)

    def test_month_operations(self):
        self.assertEquals(len(list(Month('2012-12-12'))), 31)
        self.assertEquals(len(list(Month('2012-12-12').weeks)), 6)

        previous = Month('2012-01-05')-1
        self.assertEquals(previous.first.year, 2011)
        self.assertEquals(previous.first.weekday, 4)
        self.assertEquals(previous.last.year, 2011)
        self.assertEquals(previous.last.weekday, 6)

        next = Month('2011-02-25')+1
        self.assertEquals(next.last.month, 3)
        self.assertEquals(next.last.weekday, 4)






