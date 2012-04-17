#!/usr/bin/python
"""
Class to parse and represent local calendar,suited for walking weeks and 
months and to get working days for certain calendar date week easily.
"""

import time,datetime,calendar

# Default first day of week: range 0 (sunday) to 6 (saturday)
WEEK_START_DEFAULT = 1

# Default number of workdays per week
WORKDAYS_PER_WEEK = 5

# Only used for parameter parsing in Week class, not for output
WEEKDAY_NAMES = [
    'Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'
]

class DatesError(Exception):
    """
    Exceptions raised when parsing dates
    """
    def __str__(self):  
        return self.args[0]

class Day(object):
    """
    Presentation of one day
    """
    def __init__(self,timeval=None,input_format='%Y-%m-%d',output_format='%Y-%m-%d'):
        if timeval is None:
            dateval = time.localtime()
        elif input_format is None:
            try:
                dateval = time.localtime(timeval)
            except ValueError:
                raise DatesError('Invalid timestamp: %s' % timeval)
        else:
            try:
                dateval = time.strptime(str(timeval),input_format)
            except ValueError:
                raise DatesError(
                    'Error parsing %s in format %s' % (timeval,input_format)
                )

        self.output_format = output_format
        self.timestamp = long(time.mktime(time.strptime(
            '-'.join('%02d' % x for x in dateval[:3]), '%Y-%m-%d'
        )))
        self.timetuple = time.localtime(self.timestamp)
        #noinspection PyTypeChecker
        self.datetime = datetime.datetime.fromtimestamp(self.timestamp)
        self.isoweekday = time.localtime(self.timestamp).tm_wday

    def __str__(self):
        return time.strftime(self.output_format,time.localtime(self.timestamp))

    def __cmp__(self,day):
        if self.timestamp == day: return 0
        if self.timestamp < day: return -1
        if self.timestamp > day: return 1

    def __hash__(self):
        return self.timestamp

    def __int__(self):
        return self.timestamp

    def __sub__(self,value):
        value = int(value) * 86400
        return Day(
            self.timestamp-value, input_format=None,
            output_format=self.output_format
        )

    def __add__(self,value):
        value = int(value) * 86400
        return Day(
            self.timestamp+value, input_format=None,
            output_format=self.output_format
        )

class Week(object):
    """
    Class for a week.
    """
    def __init__(self,timeval=None,input_format='%Y-%m-%d',
                 output_format='%Y-%m-%d',firstweekday=WEEK_START_DEFAULT,
                 workdays=None,workdays_per_week=WORKDAYS_PER_WEEK):
        self.__next = 0
        self.output_format = output_format
        day = Day(
            timeval=timeval,input_format=input_format,output_format=output_format
        )

        if firstweekday in WEEKDAY_NAMES:
            firstweekday = WEEKDAY_NAMES.index(firstweekday) 
        else:
            try:
                firstweekday = int(firstweekday)
                if firstweekday<0 or firstweekday>6:
                    raise ValueError
            except ValueError:
                raise ValueError('Invalid first week day index: %s' % firstweekday) 
        self.firstweekday = firstweekday
        wday = (day.isoweekday+(7-self.firstweekday)+1) % 7

        self.first = day-wday
        self.last  = self.first + 6
        self.weeknumber = int(time.strftime('%U',self.first.timetuple))
        self.timestamps = [self.first.timestamp+i*86400 for i in range(0,7)]

        self.workdays = []
        if workdays is not None:
            if type(workdays) != list:
                raise ValueError(
                    'Invalid workdays index list parameter: %s' % workdays
                )
            for i in workdays:
                try: 
                    i = int(i)
                    if i<0 or i>6:
                        raise ValueError
                    self.workdays.append(self[i])
                except ValueError:
                    raise ValueError(
                        'Invalid workdays index list parameter: %s' % workdays
                    )
                    
        else:
            try:
                workdays_per_week = int(workdays_per_week)
                if workdays_per_week<0 or workdays_per_week>7:
                    raise ValueError
            except ValueError:
                raise ValueError(
                    'Invalid value for workdays_per_week: %s' % workdays_per_week
                )
            self.workdays = [self[i] for i in filter(lambda 
                i: i<=6, range(0,workdays_per_week)
            )]
        self.workdays.sort()

    def __hash__(self):
        return self.first.timestamp

    def __int__(self):
        return 7 * 86400

    def __getitem__(self,attr):
        try:
            index = int(attr)
            if index < 0 or index > 6:
                raise ValueError
            return self.first + index
        except ValueError:
            pass
        raise IndexError('Invalid week day index: %s' % attr)


    def __sub__(self,value):
        value = int(value) * 7 * 86400
        return Week( self.first.timestamp-value, None,
            firstweekday=self.firstweekday,
            output_format=self.output_format
        )

    def __add__(self,value):
        value = int(value) * 7 * 86400
        return Week( self.first.timestamp+value, None,
            firstweekday=self.firstweekday,
            output_format=self.output_format
        )

    def __str__(self):
        return '%s - %s' % (self.first,self.last)

    def __iter__(self):
        return self

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
    Class for a month.
    """
    def __init__(self,timeval=None,input_format='%Y-%m-%d',
            output_format='%Y-%m-%d',firstweekday=WEEK_START_DEFAULT):

        self.__next = 0
        self.output_format = output_format

        day = Day( 
            timeval=timeval, 
            input_format=input_format,
            output_format=output_format
        )
        day_tm = day.timetuple 
        if day_tm.tm_mday == 1:
            self.first = day
        else:
            self.first = day - (day_tm.tm_mday-1)

        self.days = calendar.monthrange(*(self.first.timetuple[0:2]))[1]
        self.last  = self.first+(self.days-1)

        self.weeks = []
        self.firstweekday = firstweekday
        week = Week( self.first.timestamp, None,
            firstweekday=firstweekday,
            output_format=self.output_format
        )
        while int(week.first.timestamp) <= int(self.last.timestamp):
            self.weeks.append(week)
            week+=1
        self.timestamps = [self.first.timestamp+i*86400 for i in range(0,self.days)]

    def __hash__(self):
        return self.first.timestamp

    def __getitem__(self,attr):
        try:
            index = int(attr)
            if index < 0 or index >= self.days:
                raise ValueError
            return self.first + index
        except ValueError:
            pass
        raise IndexError(
            'Invalid month day index: %s (month has %d days)' % (attr,self.days)
        )

    def __str__(self):
         return time.strftime('%B %Y',self.first.timetuple)

    def __len__(self):
        return self.days

    def __add__(self,value):
        value = int(value) 
        if not value:
            return self
        m = self
        for i in range(0,value):
            m = Month(m.first.timestamp+m.days*86400, None,
                firstweekday=self.firstweekday,output_format=self.output_format
            )
        return m

    def __sub__(self,value):
        value = int(value) 
        if not value:
            return self
        m = self
        for i in range(0,value):
            m = Month(m.first.timestamp-86400, None,
                firstweekday=self.firstweekday, output_format=self.output_format
            )
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

if __name__ == '__main__':
    mon = Month('2009-02-14',firstweekday=6)
    for week in mon.weeks:
        for d in filter(lambda d: d.timestamp in mon.timestamps, week.workdays):
            print d

