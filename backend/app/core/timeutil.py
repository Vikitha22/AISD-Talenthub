"""All datetimes are stored as naive UTC. Input with a timezone is converted to UTC;
input without a timezone is treated as UTC. Output always carries a trailing 'Z'."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def fmt(dt: datetime) -> str:
    """UTC string used in messages: 'YYYY-MM-DD HH:MM UTC'. Readable as-is; the web UI rewrites it
    into the viewer's local time."""
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def iso(dt: datetime | None) -> str | None:
    """Serialise a naive-UTC datetime as ISO-8601 with a trailing Z (so browsers parse it as UTC)."""
    return None if dt is None else dt.replace(microsecond=0).isoformat() + "Z"
