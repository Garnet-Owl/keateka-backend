import calendar
from datetime import datetime, timedelta
from typing import Dict, Optional, Union

import pytz


class TimeUtils:
    """Utility class for time-related operations."""

    DEFAULT_TIMEZONE = "Africa/Nairobi"

    @staticmethod
    def generate_timestamp(tz: Optional[str] = None) -> str:
        """
        Generate timestamp in the format required by M-PESA (YYYYMMddHHmmss).

        Args:
            tz: Optional timezone (defaults to Africa/Nairobi)

        Returns:
            str: Formatted timestamp string
        """
        current_time = TimeUtils.get_current_time(tz)
        return current_time.strftime("%Y%m%d%H%M%S")

    @staticmethod
    def get_current_time(tz: Optional[str] = None) -> datetime:
        """Get current time in specified timezone."""
        timezone = pytz.timezone(tz or TimeUtils.DEFAULT_TIMEZONE)
        return datetime.now(timezone)

    @staticmethod
    def to_timezone(dt: datetime, tz: Optional[str] = None) -> datetime:
        """Convert datetime to specified timezone."""
        if not dt.tzinfo:
            dt = pytz.UTC.localize(dt)
        target_tz = pytz.timezone(tz or TimeUtils.DEFAULT_TIMEZONE)
        return dt.astimezone(target_tz)

    @staticmethod
    def parse_datetime(
        datetime_str: str,
        format_str: Optional[str] = None,
        tz: Optional[str] = None,
    ) -> datetime:
        """Parse datetime string to datetime object."""
        if format_str:
            dt = datetime.strptime(datetime_str, format_str)
        else:
            # Try common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(datetime_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                msg = f"Could not parse datetime string: {datetime_str}"
                raise ValueError(msg)

        if tz:
            dt = pytz.timezone(tz).localize(dt)
        return dt

    @staticmethod
    def format_datetime(
        dt: datetime,
        format_str: Optional[str] = None,
        tz: Optional[str] = None,
    ) -> str:
        """Format datetime to string."""
        if tz:
            dt = TimeUtils.to_timezone(dt, tz)
        return dt.strftime(format_str or "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def get_day_boundaries(dt: Optional[datetime] = None, tz: Optional[str] = None) -> Dict[str, datetime]:
        """Get start and end of day for given datetime."""
        if not dt:
            dt = TimeUtils.get_current_time(tz)
        elif not dt.tzinfo:
            dt = pytz.timezone(tz or TimeUtils.DEFAULT_TIMEZONE).localize(dt)

        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1, microseconds=-1)

        return {"start": start, "end": end}

    @staticmethod
    def get_week_boundaries(dt: Optional[datetime] = None, tz: Optional[str] = None) -> Dict[str, datetime]:
        """Get start and end of week for given datetime."""
        if not dt:
            dt = TimeUtils.get_current_time(tz)
        elif not dt.tzinfo:
            dt = pytz.timezone(tz or TimeUtils.DEFAULT_TIMEZONE).localize(dt)

        start = dt - timedelta(days=dt.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7, microseconds=-1)

        return {"start": start, "end": end}

    @staticmethod
    def get_month_boundaries(dt: Optional[datetime] = None, tz: Optional[str] = None) -> Dict[str, datetime]:
        """Get start and end of month for given datetime."""
        if not dt:
            dt = TimeUtils.get_current_time(tz)
        elif not dt.tzinfo:
            dt = pytz.timezone(tz or TimeUtils.DEFAULT_TIMEZONE).localize(dt)

        start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(dt.year, dt.month)[1]
        end = dt.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

        return {"start": start, "end": end}

    @staticmethod
    def calculate_duration(start: datetime, end: Optional[datetime] = None, unit: str = "seconds") -> Union[int, float]:
        """
        Calculate duration between two datetimes.

        Args:
            start: Start datetime
            end: End datetime (defaults to current time)
            unit: Unit of duration ("seconds", "minutes", "hours", "days")
        """
        if not end:
            end = TimeUtils.get_current_time(start.tzinfo.zone if start.tzinfo else None)

        duration = end - start

        if unit == "seconds":
            return duration.total_seconds()
        if unit == "minutes":
            return duration.total_seconds() / 60
        if unit == "hours":
            return duration.total_seconds() / 3600
        if unit == "days":
            return duration.days
        msg = f"Invalid duration unit: {unit}"
        raise ValueError(msg)

    @staticmethod
    def is_business_hours(
        dt: Optional[datetime] = None,
        start_hour: int = 9,
        end_hour: int = 17,
        tz: Optional[str] = None,
    ) -> bool:
        """Check if given time is within business hours."""
        if not dt:
            dt = TimeUtils.get_current_time(tz)
        elif not dt.tzinfo:
            dt = pytz.timezone(tz or TimeUtils.DEFAULT_TIMEZONE).localize(dt)

        return (
            dt.weekday() < 5  # Monday = 0, Friday = 4
            and start_hour <= dt.hour < end_hour
        )
