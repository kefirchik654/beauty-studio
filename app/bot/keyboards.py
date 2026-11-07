from __future__ import annotations

from datetime import date, datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from . import texts
from .callbacks import Appt, CancelAsk, CancelYes, Day, Menu, Mst, Ok, Slot, Svc

MAIN_BTN = InlineKeyboardButton(text="🏠 Главное меню", callback_data=Menu(to="main").pack())


def main_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for text, to in [
        ("📅 Записаться онлайн", "book"),
        ("🗓 Мои записи", "my"),
        ("💇 Наши услуги", "services"),
        ("👩‍🎨 Наши мастера", "masters"),
        ("📍 Адрес и контакты", "contacts"),
        ("💬 Связаться с салоном", "contact_admin"),
    ]:
        b.button(text=text, callback_data=Menu(to=to))
    b.adjust(1)
    return b.as_markup()


def services_kb(services) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in services:
        label = f"{s['name']} — {texts.money(s['price'], s['price_from'])}"
        b.button(text=label, callback_data=Svc(id=s["id"]))
    b.adjust(1)
    b.row(MAIN_BTN)
    return b.as_markup()


def masters_kb(svc_id: int, masters) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for m in masters:
        b.button(text=f"👩 {m['name']}", callback_data=Mst(svc=svc_id, id=m["id"]))
    if len(masters) > 1:
        b.button(text="⚡ Любой свободный мастер", callback_data=Mst(svc=svc_id, id=0))
    b.adjust(1)
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=Menu(to="book").pack()))
    return b.as_markup()


def days_kb(svc_id: int, mst_id: int, days: list[tuple[date, bool]], today: date) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for d, has in days:
        label = texts.day_button(d, today) if has else f"🚫 {texts.day_button(d, today)}"
        b.button(text=label, callback_data=Day(svc=svc_id, mst=mst_id, d=d.strftime("%Y%m%d")))
    b.adjust(1)
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=Svc(id=svc_id).pack()))
    return b.as_markup()


def times_kb(svc_id: int, mst_id: int, day: date, slots: list[datetime]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in slots:
        b.button(
            text=s.strftime("%H:%M"),
            callback_data=Slot(svc=svc_id, mst=mst_id, d=day.strftime("%Y%m%d"), t=s.strftime("%H%M")),
        )
    b.adjust(3)
    b.row(InlineKeyboardButton(text="⬅️ Другая дата", callback_data=Mst(svc=svc_id, id=mst_id).pack()))
    return b.as_markup()


def confirm_kb(svc_id: int, mst_id: int, d: str, t: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Подтвердить запись", callback_data=Ok(svc=svc_id, mst=mst_id, d=d, t=t))
    b.button(text="✏️ Изменить", callback_data=Day(svc=svc_id, mst=mst_id, d=d))
    b.button(text="❌ Отменить", callback_data=Menu(to="main"))
    b.adjust(1)
    return b.as_markup()


def after_booking_kb(appt_id: int, map_url: str | None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🗓 Мои записи", callback_data=Menu(to="my"))
    if map_url:
        b.row(InlineKeyboardButton(text="📍 Как добраться", url=map_url))
    b.row(MAIN_BTN)
    b.adjust(1)
    return b.as_markup()


def my_appointments_kb(appts, tz) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for a in appts:
        start = a["starts_at"].astimezone(tz)
        b.button(
            text=f"{texts.date_long(start.date())}, {start:%H:%M} — {a['service_name']}",
            callback_data=Appt(id=a["id"]),
        )
    b.adjust(1)
    b.row(MAIN_BTN)
    return b.as_markup()


def appt_kb(appt_id: int, can_cancel: bool, phone: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if can_cancel:
        b.button(text="❌ Отменить запись", callback_data=CancelAsk(id=appt_id))
    b.button(text="⬅️ Мои записи", callback_data=Menu(to="my"))
    b.adjust(1)
    return b.as_markup()


def cancel_confirm_kb(appt_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Да, отменить", callback_data=CancelYes(id=appt_id))
    b.button(text="Нет, оставить", callback_data=Appt(id=appt_id))
    b.adjust(2)
    return b.as_markup()


def back_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[MAIN_BTN]])
