from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def today_in_zone(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


def validate_timezone(tz_name: str) -> str:
    try:
        ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as e:
        raise ValueError("invalid timezone") from e
    return tz_name


def today_in_app(tz_name: str | None = None) -> date:
    from financas_app.app.settings import get_settings

    tz = tz_name or get_settings().app_timezone
    return today_in_zone(tz)


def first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def ensure_period_valid(start: date, end: date) -> None:
    if start > end:
        raise ValueError("invalid period")


def add_one_month(d: date) -> date:
    if d.month == 12:
        y, m = d.year + 1, 1
    else:
        y, m = d.year, d.month + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def advance_by_frequency(d: date, frequency: str) -> date:
    if frequency == "daily":
        return d + timedelta(days=1)
    if frequency == "weekly":
        return d + timedelta(days=7)
    if frequency == "monthly":
        return add_one_month(d)
    raise ValueError("invalid frequency")
