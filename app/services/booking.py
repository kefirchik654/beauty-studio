"""Бизнес-логика записи: свободные слоты по мастерам и безопасное создание записи."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import asyncpg

from .. import db
from .slots import free_starts


def salon_tz(salon) -> ZoneInfo:
    return ZoneInfo(salon["tz"])


def salon_now(salon) -> datetime:
    return datetime.now(timezone.utc).astimezone(salon_tz(salon))


async def master_slots(pool, salon, service, master_id: int, day: date) -> list[datetime]:
    tz = salon_tz(salon)
    work, breaks = await db.day_schedule(pool, master_id, day)
    if not work:
        return []
    day_start = datetime.combine(day, time(0), tzinfo=tz)
    busy = await db.busy_ranges(pool, master_id, day_start, day_start + timedelta(days=1))
    return free_starts(
        day, tz, work, breaks, busy,
        duration_min=service["duration_min"],
        buffer_min=service["buffer_min"],
        step_min=salon["slot_step_minutes"],
        now=salon_now(salon),
        min_lead_min=salon["min_lead_minutes"],
    )


async def day_slots(pool, salon, service, master_ids: list[int], day: date) -> dict[datetime, list[int]]:
    """{время начала: [мастера, у которых оно свободно]}. Для «любого мастера» объединяет всех."""
    result: dict[datetime, list[int]] = {}
    for mid in master_ids:
        for s in await master_slots(pool, salon, service, mid, day):
            result.setdefault(s, []).append(mid)
    return dict(sorted(result.items()))


async def available_days(pool, salon, service, master_ids: list[int], count: int = 5) -> list[tuple[date, bool]]:
    """Ближайшие `count` дат и признак наличия свободных окон."""
    today = salon_now(salon).date()
    horizon = salon["booking_horizon_days"]
    days = []
    for i in range(min(count, horizon)):
        d = today + timedelta(days=i)
        slots = await day_slots(pool, salon, service, master_ids, d)
        days.append((d, bool(slots)))
    return days


@dataclass
class BookResult:
    status: str  # ok | busy | duplicate | invalid
    appointment: asyncpg.Record | None = None
    master_name: str | None = None


async def book(pool, salon, client, service, master_id: int, starts_at: datetime) -> BookResult:
    """Создать запись. master_id == 0 означает «любой свободный мастер».

    Порядок: повторная проверка слота -> выбор мастера -> вставка в транзакции.
    Если два клиента успели одновременно, второй получит ExclusionViolation от базы,
    и мы вернём status='busy'.
    """
    salon_id = salon["id"]
    masters = await db.masters_for_service(pool, salon_id, service["id"])
    allowed = {m["id"]: m for m in masters}
    candidate_ids = list(allowed) if master_id == 0 else ([master_id] if master_id in allowed else [])
    if not candidate_ids:
        return BookResult("invalid")

    # Повторная проверка: время должно всё ещё входить в список свободных у кого-то из кандидатов.
    day = starts_at.astimezone(salon_tz(salon)).date()
    slots = await day_slots(pool, salon, service, candidate_ids, day)
    free_for = slots.get(starts_at.astimezone(salon_tz(salon)))
    if not free_for:
        return BookResult("busy")

    # «Любой мастер»: выбираем наименее загруженного в этот день.
    tz = salon_tz(salon)
    d0 = datetime.combine(day, time(0), tzinfo=tz)
    if len(free_for) > 1:
        loads = {m: await db.day_load(pool, m, d0, d0 + timedelta(days=1)) for m in free_for}
        chosen = min(free_for, key=lambda m: (loads[m], m))
    else:
        chosen = free_for[0]

    price = allowed[chosen]["price"]
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                dup = await db.find_active_duplicate(conn, client["id"], service["id"], starts_at)
                if dup:
                    return BookResult("duplicate", dup, allowed.get(dup["master_id"], {}).get("name"))
                appt = await db.insert_appointment(
                    conn, salon_id=salon_id, client_id=client["id"], master_id=chosen,
                    service=service, price=price, starts_at=starts_at,
                )
    except asyncpg.exceptions.ExclusionViolationError:
        return BookResult("busy")
    return BookResult("ok", appt, allowed[chosen]["name"])


def can_self_cancel(salon, starts_at: datetime) -> bool:
    return starts_at - datetime.now(timezone.utc) >= timedelta(hours=salon["cancel_before_hours"])
