from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from core.models.enums import Frequency


def calculate_next_run(
    frequency: Frequency,
    schedule_time: str | None = None,
    tz_name: str = "UTC",
    now: datetime | None = None,
) -> datetime | None:
    """
    Computes the exact next execution timestamp accounting for wall-clock time and timezone.
    """
    if frequency == Frequency.once:
        return None

    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")

    now_tz = (now or datetime.now(timezone.utc)).astimezone(tz)

    target_hour = 8
    target_minute = 0
    if schedule_time and ":" in schedule_time:
        try:
            parts = schedule_time.split(":")
            target_hour = int(parts[0])
            target_minute = int(parts[1])
        except (ValueError, IndexError):
            pass

    if frequency == Frequency.hourly:
        candidate = now_tz.replace(minute=target_minute, second=0, microsecond=0)
        if candidate <= now_tz:
            candidate += timedelta(hours=1)
        return candidate.astimezone(timezone.utc)

    elif frequency == Frequency.daily:
        candidate = now_tz.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if candidate <= now_tz:
            candidate += timedelta(days=1)
        return candidate.astimezone(timezone.utc)

    elif frequency == Frequency.weekly:
        candidate = now_tz.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if candidate <= now_tz:
            candidate += timedelta(days=7)
        return candidate.astimezone(timezone.utc)

    elif frequency == Frequency.monthly:
        import calendar
        candidate = now_tz.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if candidate <= now_tz:
            year = candidate.year + (candidate.month // 12)
            month = (candidate.month % 12) + 1
            max_day = calendar.monthrange(year, month)[1]
            candidate = candidate.replace(year=year, month=month, day=min(candidate.day, max_day))
        return candidate.astimezone(timezone.utc)

    return (now_tz + timedelta(days=1)).astimezone(timezone.utc)
