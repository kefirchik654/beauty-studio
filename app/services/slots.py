"""Чистая логика расчёта свободных слотов (без базы и Telegram): легко тестируется."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

Interval = tuple[time, time]
BusyRange = tuple[datetime, datetime]  # (starts_at, busy_until), aware datetimes


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _to_time(m: int) -> time:
    return time(m // 60, m % 60)


def subtract_breaks(work: list[Interval], breaks: list[Interval]) -> list[Interval]:
    """Вычесть перерывы из рабочих интервалов: 10-19 минус 13-14 = 10-13 и 14-19."""
    result: list[Interval] = []
    for w_start, w_end in work:
        cur = _minutes(w_start)
        end = _minutes(w_end)
        for b_start, b_end in sorted(breaks):
            bs, be = _minutes(b_start), _minutes(b_end)
            if be <= cur or bs >= end:
                continue
            if bs > cur:
                result.append((_to_time(cur), _to_time(bs)))
            cur = max(cur, be)
        if cur < end:
            result.append((_to_time(cur), _to_time(end)))
    return result


def free_starts(
    day: date,
    tz: ZoneInfo,
    work: list[Interval],
    breaks: list[Interval],
    busy: list[BusyRange],
    duration_min: int,
    buffer_min: int,
    step_min: int,
    now: datetime,
    min_lead_min: int = 60,
) -> list[datetime]:
    """Свободные времена начала услуги в день `day` (aware-datetime в поясе салона).

    Слот подходит, если вся услуга помещается в рабочий интервал (после вычета
    перерывов), а промежуток [начало, конец + буфер) не пересекается с записями.
    """
    dur = timedelta(minutes=duration_min)
    buf = timedelta(minutes=buffer_min)
    step = timedelta(minutes=step_min)
    earliest = now + timedelta(minutes=min_lead_min)

    out: list[datetime] = []
    for w_start, w_end in subtract_breaks(work, breaks):
        cur = datetime.combine(day, w_start, tzinfo=tz)
        end = datetime.combine(day, w_end, tzinfo=tz)
        while cur + dur <= end:
            if cur >= earliest and not any(
                cur < b_end and cur + dur + buf > b_start for b_start, b_end in busy
            ):
                out.append(cur)
            cur += step
    return out
