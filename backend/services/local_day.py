"""The learner's day in local time (01.11.2026).

The database stores naive UTC (``datetime.now(timezone.utc)``), but a learning day
is the learner's calendar day on the PC (Poland: UTC+1 in winter, UTC+2 in summer).
Counting by ``func.date(created_at)`` put everything done between midnight and
01:00/02:00 into the previous day: the streak, "today's lesson", the daily test and
the hub's summary all disagreed with the clock on the wall.
"""
from datetime import date, datetime, time, timedelta, timezone

# None = the PC's local time zone; tests set a fixed zone (time.tzset() does not exist on Windows)
LOCAL_TZ = None


def local_date(moment: datetime) -> date:
    """Local calendar day of a stored moment (naive values are UTC)."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(LOCAL_TZ).date()


def local_today() -> date:
    return datetime.now(timezone.utc).astimezone(LOCAL_TZ).date()


def utc_range(day: date) -> tuple[datetime, datetime]:
    """[start, end) of a local day as naive UTC, for filtering stored columns."""
    def utc(d: date) -> datetime:
        if LOCAL_TZ is None:
            moment = datetime.combine(d, time.min).astimezone()  # local midnight, local offset
        else:
            moment = datetime.combine(d, time.min, tzinfo=LOCAL_TZ)
        return moment.astimezone(timezone.utc).replace(tzinfo=None)
    return utc(day), utc(day + timedelta(days=1))


def on_local_day(column, day: date):
    """SQLAlchemy filter: ``column`` (naive UTC) falls on local ``day``."""
    start, end = utc_range(day)
    return (column >= start) & (column < end)


def local_date_hour(moment: datetime) -> int:
    """Hour of the learner's clock for a stored or aware moment."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(LOCAL_TZ).hour
