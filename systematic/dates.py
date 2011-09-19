#!/usr/bin/python
"""
Class to parse and represent local calendar,suited for walking weeks and 
months and to get working days for certain calendar date week easily.

Copyright Ilkka Tuohela <hile@iki.fi>, 2007-2011.
"""

import sys,os,time,datetime,calendar

# Start default from monday (range from 0=sun 6=sat)
WEEK_START_DEFAULT = 1
# Only used for parameter parsing in Week class, not for output
WEEKDAY_NAMES = [
    'Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'
]

class DatesError(Exception):
    def __str__(self):  
        return self.args[0]

class Day(object):
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

    def __getattr__(self,item):
        if item == 'timetuple':
            return time.localtime(self.timestamp)
        elif item == 'datetime':
            return datetime.datetime.fromtimestamp(self.timestamp)
        raise AttributeError('No such Day item %s' % item)

    def __str__(self):
        return time.strftime(self.output_format,time.localtime(self.timestamp))

    def __cmp__(self,day):
        if self.timestamp == day: return 0
        if self.timestamp < day: return -1
        if self.timestamp > day: return 1

    def __int__(self):
        return self.timestamp

    def __sub__(self,value):
        value = int(value) * 86400
        return Day( self.timestamp-value, input_format=None,
            output_format=self.output_format
        )

    def __add__(self,value):
        value = int(value) * 86400
        return Day( self.timestamp+value, input_format=None,
            output_format=self.output_format
        )

    def isoweekday(self):
        return time.localtime(self.timestamp).tm_wday

class Week(object):
    def __init__(self,timeval=None,input_format='%Y-%m-%d',
                 output_format='%Y-%m-%d',weekstart=WEEK_START_DEFAULT):
        self.__next = 0
        self.output_format = output_format
        day = Day(timeval=timeval,input_format=input_format,output_format=output_format) 
        if weekstart in WEEKDAY_NAMES:
            weekstart = WEEKDAY_NAMES.index(weekstart) 
        wday = (day.isoweekday()+(7-weekstart)+1) % 7

        self.first = day-wday
        self.last  = self.first + 6
        self.weekstart = weekstart
        self.weeknumber = int(time.strftime('%U',self.first.timetuple))

    def __getattr__(self,item):
        if item == 'days':  
            return iter(self)
        raise AttributeError('No such Week item %s' % item)

    def __int__(self):
        return 7 * 86400

    def __sub__(self,value):
        value = int(value) * 7 * 86400
        return Week( self.first.timestamp-value, None,
            weekstart=self.weekstart,
            output_format=self.output_format
        )

    def __add__(self,value):
        value = int(value) * 7 * 86400
        return Week( self.first.timestamp+value, None,
            weekstart=self.weekstart,
            output_format=self.output_format
        )

    def __str__(self):
        return '%s - %s' % (self.first,self.last)

    def __iter__(self):
        return self

    def next(self):
        if self.__next < 7:
            day = self.first + self.__next
            self.__next += 1
        else:
            self.__next = 0
            raise StopIteration
        return day

    def timestamps(self):
        return [self.first.timestamp+i*86400 for i in range(0,7)]

class Month(object):
    def __init__(self,timeval=None,input_format='%Y-%m-%d',
            output_format='%Y-%m-%d',weekstart=WEEK_START_DEFAULT):

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
        self.weekstart = weekstart
        week = Week( self.first.timestamp, None,
            weekstart=weekstart,
            output_format=self.output_format
        )
        while int(week.first.timestamp) <= int(self.last.timestamp):
            self.weeks.append(week)
            week = week+1

    def __str__(self):
         return time.strftime('%B %Y',self.first.timetuple)

    def __add__(self,value):
        value = int(value) 
        if value == 0: 
            return self
        m = self
        for i in range(0,value):
            m = Month(m.first.timestamp+m.days*86400, None,
                weekstart=self.weekstart,output_format=self.output_format
            )
        return m

    def __sub__(self,value):
        value = int(value) 
        if value == 0: 
            return self
        m = self
        for i in range(0,value):
            m = Month(m.first.timestamp-86400, None,
                weekstart=self.weekstart, output_format=self.output_format
            )
        return m

    def __len__(self):
        return self.days

    def __iter__(self):
        return self

    def next(self):
        if self.__next < self.days:
            day = self.first + self.__next
            self.__next += 1
        else:
            self.__next = 0
            raise StopIteration
        return day

    def timestamps(self):
        return [self.first.timestamp+i*86400 for i in range(0,self.days)]

if __name__ == '__main__':
    m = Month(weekstart='Monday')
    for w in m.weeks:
        print w
        for d in w:
            print d
    sys.exit(0)

    w = Week(weekstart='Saturday')
    for i in range(0,6):
        print 'Week %s\n%s'  % (w,' '.join('%s' % d.datetime for d in w.days))
        w-= 1

