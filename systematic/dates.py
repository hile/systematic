"""
Class to parse and represent local calendar.

Suited for walking weeks and months and to get working days for
certain calendar date week easily.
"""
from __future__ import unicode_literals

import time
import calendar
import collections

from builtins import int
from datetime import datetime, date, timedelta

from systematic.log import Logger

DEFAULT_DATE_FORMAT = '%Y-%m-%d'

# Default first day of week: range 0 (sunday) to 6 (saturday)
WEEK_START_DEFAULT = 1
# Default number of workdays per week
WORKDAYS_PER_WEEK = 5

# Only used for parameter parsing in Week class, not for output
WEEKDAY_NAMES = [
    'Sunday',
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday'
]


class DatesError(Exception):
    """
    Exceptions raised when parsing dates
    """
    pass


class Day(object):
    """
    Extension of datetime.date object supporting iteration and some basic operations
    """
    def __init__(self, value=None, input_format=None):
        self.log = Logger('dates').default_stream

        if value is None:
            self.value = datetime.now().date()

        elif isinstance(value, Day):
            self.value = value.value

        elif isinstance(value, date):
            self.value = value

        elif isinstance(value, datetime):
            self.value = value.date()

        elif isinstance(value, time.struct_time):
            self.value = date(*value[:3])

        elif isinstance(value, str) and input_format is None and value == '':
            self.value = datetime.now().date()

        else:
            input_format = input_format is not None and input_format or DEFAULT_DATE_FORMAT
            try:
                self.value = datetime.strptime(str(value), input_format).date()
            except ValueError:
                try:
                    self.value = date(*time.localtime(int(value))[:3])
                except ValueError:
                    raise DatesError('Error parsing date: {0}'.format(value))

    def __getattr__(self, attr):
        if attr == 'weekday':
            return self.value.isoweekday()
        return getattr(self.value, attr)

    def __str__(self):
        return self.value.strftime(DEFAULT_DATE_FORMAT)

    def __repr__(self):
        return self.__str__()

    def __int__(self):
        return int(self.value.strftime('%s'))

    def __hash__(self):
        return int(self)

    def __eq__(self, value):
        return int(self) == int(value)

    def __ne__(self, value):
        return int(self) != int(value)

    def __gt__(self, value):
        return int(self) > int(value)

    def __lt__(self, value):
        return int(self) < int(value)

    def __le__(self, value):
        return int(self) <= int(value)

    def __ge__(self, value):
        return int(self) >= int(value)

    def __sub__(self, value):
        try:
            return Day(self.value - timedelta(days=value))
        except ValueError:
            raise DatesError('Invalid day delta: {0}'.format(value))

    def __add__(self, value):
        try:
            return Day(self.value + timedelta(days=value))
        except ValueError:
            raise DatesError('Invalid day delta: {0}'.format(value))

    def strftime(self, value):
        return self.value.strftime(value)


class Week(object):
    """
    Week instance supporting iteration
    """
    def __init__(self, value=None, input_format=DEFAULT_DATE_FORMAT,
                 firstweekday=WEEK_START_DEFAULT, workdays=None,
                 workdays_per_week=WORKDAYS_PER_WEEK):

        self.__next = 0
        self.log = Logger('dates').default_stream

        day = Day(value=value, input_format=input_format)

        if firstweekday in WEEKDAY_NAMES:
            self.firstweekday = WEEKDAY_NAMES.index(firstweekday)
        else:
            try:
                self.firstweekday = int(firstweekday)
                if self.firstweekday < 0 or self.firstweekday > 6:
                    raise ValueError
            except ValueError:
                raise ValueError('Invalid first week day index: {0}'.format(firstweekday))
        wday = (day.value.isoweekday()+(7-self.firstweekday)) % 7

        self.first = day - wday
        self.last = self.first + 6
        self.weeknumber = int(self.first.value.strftime('%U'))

        self.workdays = []
        if workdays is not None:
            if not isinstance(workdays, collections.Iterable):
                raise ValueError('Invalid workdays index list parameter: {0}'.format(workdays))
            for i in workdays:
                try:
                    i = int(i)
                    if i < 0 or i > 6:
                        raise ValueError
                    self.workdays.append(self.first + i)
                except ValueError:
                    raise ValueError('Invalid workdays index list parameter: {0}'.format(workdays))

        else:
            try:
                workdays_per_week = int(workdays_per_week)
                if workdays_per_week < 0 or workdays_per_week > 7:
                    raise ValueError
            except ValueError:
                raise ValueError('Invalid value for workdays_per_week: {0}'.format(workdays_per_week))
            self.workdays = []
            for i in range(0, workdays_per_week):
                if i <= 6:
                    self.workdays.append(self[i])

        self.workdays.sort()

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return 'Week {0} {1} - {2}'.format(self.first.strftime('%U'), self.first, self.last)

    def __hash__(self):
        return (self.first)

    def __int__(self):
        self.first.strftime('%U')

    def __getattr__(self, attr):
        return getattr(self.first.value, attr)

    def __getitem__(self, attr):
        try:
            index = int(attr)
            if index < 0 or index > 6:
                raise ValueError
            return self.first + index
        except ValueError:
            pass

        raise IndexError('Invalid week day index: {0}'.format(attr))

    def __sub__(self, value):
        return Week(self.first-7*int(value), None, firstweekday=self.firstweekday)

    def __add__(self, value):
        return Week(self.first+7*value, None, firstweekday=self.firstweekday)

    def __iter__(self):
        return self

    @property
    def previous_week(self):
        """Previous week

        """
        return self - 1

    @property
    def next_week(self):
        """Previous week

        """
        return self - 1

    def next(self):
        """
        Return next day object in this week, until exhausted
        """
        if self.__next < 7:
            day = self.first + self.__next
            self.__next += 1
        else:
            self.__next = 0
            raise StopIteration

        return day


class Month(object):
    """
    Month instance supporting iteration
    """
    def __init__(self, value=None, input_format=DEFAULT_DATE_FORMAT,
                 firstweekday=WEEK_START_DEFAULT):

        self.__next = 0
        self.log = Logger('dates').default_stream

        self.first = Day(Day(value=value, input_format=input_format).value.replace(day=1))
        self.days = calendar.monthrange(self.first.value.year, self.first.value.month)[1]
        self.last = self.first+(self.days-1)

        self.firstweekday = firstweekday
        self.weeks = []
        week = Week(self.first, None, firstweekday=self.firstweekday)
        while week.first <= self.last:
            self.weeks.append(week)
            week += 1

    def __repr__(self):
        return self.first.strftime('%B %Y')

    def __hash__(self):
        return (self.first)

    def __getitem__(self, attr):
        try:
            index = int(attr)
            if index < 0 or index >= self.days:
                raise ValueError
            return self.first + index
        except ValueError:
            pass

        raise IndexError('Invalid month day index: {0} (month has {1:d} days)'.format(attr, self.days))

    def __len__(self):
        return self.days

    def __sub__(self, value):
        return self.__add__(-value)

    def __add__(self, value):
        m = self
        value = int(value)
        if value >= 0:
            for _i in range(0, int(value)):
                m = Month(m.first+m.days, None, firstweekday=self.firstweekday)
        else:
            for _i in range(value, 0):
                m = Month(m.first-1, None, firstweekday=self.firstweekday)

        return m

    def __iter__(self):
        return self

    def next(self):
        """
        Return next day in month.
        Raises StopIteration when day is out of month range
        """
        if self.__next < self.days:
            day = self.first + self.__next
            self.__next += 1
        else:
            self.__next = 0
            raise StopIteration

        return day
