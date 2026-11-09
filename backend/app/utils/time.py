from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_aware(dt: datetime | None) -> datetime | None:
    """Treat naive datetimes as UTC (SQLite drops tz info; Postgres keeps it)."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
