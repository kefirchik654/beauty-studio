"""Слой доступа к данным. Каждый запрос ограничен salon_id, чтобы салоны не видели чужие данные."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

import asyncpg


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=1, max_size=10)


async def get_salon(pool, salon_id: int):
    return await pool.fetchrow("SELECT * FROM salons WHERE id = $1 AND is_active", salon_id)


async def list_services(pool, salon_id: int):
    return await pool.fetch(
        """SELECT s.*, c.name AS category FROM services s
           LEFT JOIN service_categories c ON c.id = s.category_id
           WHERE s.salon_id = $1 AND s.is_active
           ORDER BY c.sort NULLS LAST, s.name""",
        salon_id,
    )


async def get_service(pool, salon_id: int, service_id: int):
    return await pool.fetchrow(
        "SELECT * FROM services WHERE id = $1 AND salon_id = $2 AND is_active", service_id, salon_id
    )


async def masters_for_service(pool, salon_id: int, service_id: int):
    """Только активные мастера салона, которые выполняют услугу."""
    return await pool.fetch(
        """SELECT m.*, COALESCE(ms.price_override, s.price) AS price
           FROM masters m
           JOIN master_services ms ON ms.master_id = m.id
           JOIN services s ON s.id = ms.service_id AND s.salon_id = m.salon_id
           WHERE m.salon_id = $1 AND ms.service_id = $2 AND m.is_active
           ORDER BY m.name""",
        salon_id, service_id,
    )


async def list_masters(pool, salon_id: int):
    return await pool.fetch(
        "SELECT * FROM masters WHERE salon_id = $1 AND is_active ORDER BY name", salon_id
    )


async def day_schedule(pool, master_id: int, day: date):
    """Рабочие интервалы и перерывы мастера на дату с учётом исключений и отпусков."""
    exc = await pool.fetchrow(
        """SELECT kind, start_time, end_time FROM schedule_exceptions
           WHERE master_id = $1 AND $2 BETWEEN date_from AND date_to
           ORDER BY id DESC LIMIT 1""",
        master_id, day,
    )
    dow = day.weekday()
    if exc and exc["kind"] in ("day_off", "vacation"):
        return [], []
    if exc and exc["kind"] == "custom_hours":
        work = [(exc["start_time"], exc["end_time"])]
    else:
        rows = await pool.fetch(
            "SELECT start_time, end_time FROM working_hours WHERE master_id = $1 AND dow = $2",
            master_id, dow,
        )
        work = [(r["start_time"], r["end_time"]) for r in rows]
    brows = await pool.fetch(
        "SELECT start_time, end_time FROM breaks WHERE master_id = $1 AND dow = $2", master_id, dow
    )
    return work, [(r["start_time"], r["end_time"]) for r in brows]


async def busy_ranges(pool, master_id: int, day_start: datetime, day_end: datetime):
    rows = await pool.fetch(
        """SELECT starts_at, busy_until FROM appointments
           WHERE master_id = $1 AND status IN ('booked','confirmed')
             AND starts_at < $3 AND busy_until > $2""",
        master_id, day_start, day_end,
    )
    return [(r["starts_at"], r["busy_until"]) for r in rows]


async def day_load(pool, master_id: int, day_start: datetime, day_end: datetime) -> int:
    return await pool.fetchval(
        """SELECT count(*) FROM appointments WHERE master_id = $1
           AND status IN ('booked','confirmed') AND starts_at >= $2 AND starts_at < $3""",
        master_id, day_start, day_end,
    )


async def upsert_client(pool, salon_id: int, telegram_id: int, name: str):
    return await pool.fetchrow(
        """INSERT INTO clients (salon_id, telegram_id, name) VALUES ($1, $2, $3)
           ON CONFLICT (salon_id, telegram_id) DO UPDATE SET name = EXCLUDED.name
           RETURNING *""",
        salon_id, telegram_id, name,
    )


async def find_active_duplicate(conn, client_id: int, service_id: int, starts_at: datetime):
    """Защита от двойного нажатия: та же запись этого клиента на то же время уже есть."""
    return await conn.fetchrow(
        """SELECT * FROM appointments WHERE client_id = $1 AND service_id = $2
           AND starts_at = $3 AND status IN ('booked','confirmed')""",
        client_id, service_id, starts_at,
    )


async def insert_appointment(conn, *, salon_id, client_id, master_id, service, price,
                             starts_at: datetime):
    ends = starts_at + timedelta(minutes=service["duration_min"])
    busy_until = ends + timedelta(minutes=service["buffer_min"])
    return await conn.fetchrow(
        """INSERT INTO appointments
           (salon_id, client_id, master_id, service_id, service_name, price,
            starts_at, ends_at, busy_until)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *""",
        salon_id, client_id, master_id, service["id"], service["name"], price,
        starts_at, ends, busy_until,
    )


async def client_upcoming(pool, salon_id: int, telegram_id: int, now: datetime):
    return await pool.fetch(
        """SELECT a.*, m.name AS master_name FROM appointments a
           JOIN clients c ON c.id = a.client_id
           JOIN masters m ON m.id = a.master_id
           WHERE a.salon_id = $1 AND c.telegram_id = $2
             AND a.status IN ('booked','confirmed') AND a.starts_at >= $3
           ORDER BY a.starts_at""",
        salon_id, telegram_id, now,
    )


async def get_client_appointment(pool, salon_id: int, telegram_id: int, appt_id: int):
    """Запись возвращается только владельцу: клиент не может открыть чужую подменой ID."""
    return await pool.fetchrow(
        """SELECT a.*, m.name AS master_name FROM appointments a
           JOIN clients c ON c.id = a.client_id
           JOIN masters m ON m.id = a.master_id
           WHERE a.id = $1 AND a.salon_id = $2 AND c.telegram_id = $3""",
        appt_id, salon_id, telegram_id,
    )


async def cancel_appointment(pool, salon_id: int, appt_id: int):
    return await pool.fetchval(
        """UPDATE appointments SET status = 'cancelled_by_client'
           WHERE id = $1 AND salon_id = $2 AND status IN ('booked','confirmed')
           RETURNING id""",
        appt_id, salon_id,
    )
