from __future__ import annotations

from datetime import date, datetime

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
WEEKDAYS_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def money(v: int, price_from: bool = False) -> str:
    s = f"{v:,}".replace(",", " ")
    return f"{'от ' if price_from else ''}{s} ₽"


def date_long(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]}"


def day_button(d: date, today: date) -> str:
    if d == today:
        return f"Сегодня, {date_long(d)}"
    if (d - today).days == 1:
        return f"Завтра, {date_long(d)}"
    return f"{WEEKDAYS_SHORT[d.weekday()].capitalize()}, {date_long(d)}"


def appt_card(a, tz, salon_name: str | None = None) -> str:
    start: datetime = a["starts_at"].astimezone(tz)
    lines = []
    if salon_name:
        lines.append(f"🏠 Салон: {salon_name}")
    lines += [
        f"💇 Услуга: {a['service_name']}",
        f"👩 Мастер: {a['master_name']}",
        f"📅 Дата: {date_long(start.date())}",
        f"🕒 Время: {start:%H:%M}",
        f"💰 Стоимость: {money(a['price'])}",
    ]
    return "\n".join(lines)
