"""
Unit tests for dates parsers
"""

from datetime import datetime, timedelta
from systematic.dates import Day, Week, Month


def test_day_date():
    """Check Day value

    """
    today = datetime.now().date()
    day = Day()
    assert type(day.value) == type(today)
    assert day.value == today
    datetime.strptime(day.__repr__(), '%Y-%m-%d')


def test_day_add_substract():
    """Check Day operations

    """
    today = datetime.now().date()
    day = Day()

    tomorrow = day + 1
    assert isinstance(tomorrow, Day)
    assert tomorrow.value == today + timedelta(days=1)

    yesterday = day - 1
    assert isinstance(yesterday, Day)
    assert yesterday.value == today - timedelta(days=1)


def test_week_dates():
    """Test Week object

    """
    week = Week()
    assert isinstance(week.first, Day)
    assert isinstance(week.last, Day)


def test_week_add_substract():
    """Check Week operations

    """
    week = Week()

    previos_week = week - 10
    assert isinstance(previos_week, Week)

    next_week = week + 10
    assert isinstance(next_week, Week)


def test_month_dates():
    """Test Month object

    """
    month = Month()
    assert isinstance(month.first, Day)
    assert isinstance(month.last, Day)
