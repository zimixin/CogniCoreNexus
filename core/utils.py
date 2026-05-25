"""
CogniCore Nexus — общие утилиты.
Единый формат даты/времени для всей системы.
"""

from datetime import datetime, timezone, timedelta

# Единый формат: ISO 8601 с часовым поясом
# Пример: "2026-05-24T09:08:37.123456+00:00"
TIMESTAMP_FORMAT = "ISO8601_TZ"

# Компактный формат для AAAK (без микросекунд)
# Пример: "2026-05-24T09:08:37+00:00"
AAAK_TIMESTAMP_FORMAT = "ISO8601_TZ_COMPACT"


def utcnow() -> datetime:
    """
    Текущее время в UTC с явным часовым поясом.
    Замена datetime.utcnow() (deprecated в Python 3.12).
    """
    return datetime.now(timezone.utc)


def timestamp(dt: datetime | None = None) -> str:
    """
    Полный ISO 8601 таймстемп с микросекундами и часовым поясом.
    Пример: "2026-05-24T09:08:37.123456+00:00"

    Использование: для SQLite (TEXT), для отладки, для JSON.
    """
    if dt is None:
        dt = utcnow()
    return dt.isoformat()


def aaak_timestamp(dt: datetime | None = None) -> str:
    """
    Компактный таймстемп без микросекунд для AAAK-записей.
    Пример: "2026-05-24T09:08:37+00:00"

    Использование: поле :time в AAAK S-выражениях.
    """
    if dt is None:
        dt = utcnow()
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


def log_timestamp(dt: datetime | None = None) -> str:
    """
    Человеко-читаемый таймстемп для логов.
    Пример: "2026-05-24 09:08:37 UTC"
    """
    if dt is None:
        dt = utcnow()
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


if __name__ == "__main__":
    print(f"Полный:     {timestamp()}")
    print(f"AAAK:       {aaak_timestamp()}")
    print(f"Лог:        {log_timestamp()}")
    print(f"Parsed:     {datetime.fromisoformat(timestamp())}")
    print(f"Всё ок:     все три формата из одного источника")