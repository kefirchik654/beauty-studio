"""Хендлеры клиента: запись, мои записи, отмена, информационные разделы.

Состояние выбора (услуга -> мастер -> дата -> время) хранится в callback_data, поэтому
бот не держит ничего в памяти и переживает перезапуск. Все данные из callback проверяются
по базе заново: услуге, мастеру и салону доверять нельзя.
"""
from __future__ import annotations

import logging
from datetime import datetime, time

import asyncpg
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from .. import db
from ..config import ADMIN_CHAT_ID
from ..services import booking
from . import keyboards as kb
from . import texts
from .callbacks import Appt, CancelAsk, CancelYes, Day, Menu, Mst, Ok, Slot, Svc

log = logging.getLogger(__name__)
router = Router()


async def show(cb: CallbackQuery, text: str, markup) -> None:
    """Редактируем текущее сообщение, чтобы не засорять чат."""
    try:
        await cb.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        # сообщение нельзя отредактировать (например, оно с фото): отправляем новое
        await cb.message.answer(text, reply_markup=markup, parse_mode="HTML")
    try:
        await cb.answer()  # снимает «часики» с кнопки; повторный ответ на тот же callback игнорируем
    except TelegramBadRequest:
        pass


def welcome(salon) -> str:
    return f"✨ <b>Добро пожаловать в {salon['name']}!</b>\n\nРады видеть вас!\n\n{salon['greeting']}\n\nВыберите нужное действие ниже."


# ---------- главное меню ----------

@router.message(CommandStart())
async def start(message: Message, pool: asyncpg.Pool, salon):
    await db.upsert_client(pool, salon["id"], message.from_user.id, message.from_user.full_name)
    await message.answer(welcome(salon), reply_markup=kb.main_menu(), parse_mode="HTML")


@router.callback_query(Menu.filter(F.to == "main"))
async def menu_main(cb: CallbackQuery, salon):
    await show(cb, welcome(salon), kb.main_menu())


# ---------- запись ----------

@router.callback_query(Menu.filter(F.to == "book"))
async def book_start(cb: CallbackQuery, pool, salon):
    services = await db.list_services(pool, salon["id"])
    if not services:
        return await show(cb, "Пока нет доступных услуг.", kb.back_main_kb())
    await show(cb, "💇 <b>Выберите услугу</b>\n\nНа какую процедуру вы хотите записаться?", kb.services_kb(services))


@router.callback_query(Svc.filter())
async def choose_service(cb: CallbackQuery, callback_data: Svc, pool, salon):
    service = await db.get_service(pool, salon["id"], callback_data.id)
    if not service:
        return await show(cb, "Эта услуга сейчас недоступна.", kb.back_main_kb())
    masters = await db.masters_for_service(pool, salon["id"], service["id"])
    if not masters:
        return await show(cb, "Для этой услуги пока нет мастеров.", kb.back_main_kb())
    lines = [f"👩‍🎨 <b>Выберите мастера</b>\n\nУслуга: {service['name']}\n"]
    for m in masters:
        exp = f"\nОпыт работы: {m['experience_years']} лет" if m["experience_years"] else ""
        lines.append(f"<b>{m['name']}</b>{exp}\nСтоимость: {texts.money(m['price'], service['price_from'])}\n")
    await show(cb, "\n".join(lines), kb.masters_kb(service["id"], masters))


@router.callback_query(Mst.filter())
async def choose_master(cb: CallbackQuery, callback_data: Mst, pool, salon):
    service = await db.get_service(pool, salon["id"], callback_data.svc)
    if not service:
        return await show(cb, "Эта услуга сейчас недоступна.", kb.back_main_kb())
    masters = await db.masters_for_service(pool, salon["id"], service["id"])
    by_id = {m["id"]: m for m in masters}
    if callback_data.id != 0 and callback_data.id not in by_id:
        return await show(cb, "Этот мастер сейчас недоступен.", kb.back_main_kb())
    ids = list(by_id) if callback_data.id == 0 else [callback_data.id]
    master_label = "Любой свободный" if callback_data.id == 0 else by_id[callback_data.id]["name"]
    days = await booking.available_days(pool, salon, service, ids)
    today = booking.salon_now(salon).date()
    text = (f"📆 <b>Выберите дату посещения</b>\n\nУслуга: {service['name']}\n"
            f"Мастер: {master_label}\n\nВыберите удобный день.")
    await show(cb, text, kb.days_kb(service["id"], callback_data.id, days, today))


@router.callback_query(Day.filter())
async def choose_day(cb: CallbackQuery, callback_data: Day, pool, salon):
    service = await db.get_service(pool, salon["id"], callback_data.svc)
    if not service:
        return await show(cb, "Эта услуга сейчас недоступна.", kb.back_main_kb())
    masters = await db.masters_for_service(pool, salon["id"], service["id"])
    by_id = {m["id"]: m for m in masters}
    if callback_data.mst != 0 and callback_data.mst not in by_id:
        return await show(cb, "Этот мастер сейчас недоступен.", kb.back_main_kb())
    ids = list(by_id) if callback_data.mst == 0 else [callback_data.mst]
    day = datetime.strptime(callback_data.d, "%Y%m%d").date()
    slots = await booking.day_slots(pool, salon, service, ids, day)
    master_label = "Любой свободный" if callback_data.mst == 0 else by_id[callback_data.mst]["name"]
    if not slots:
        text = ("😔 На эту дату свободных окон нет.\n\nВыберите другую дату"
                + ("" if callback_data.mst == 0 else " или другого мастера") + ".")
        return await show(cb, text, kb.times_kb(service["id"], callback_data.mst, day, []))
    text = (f"🕒 <b>Выберите удобное время</b>\n\nМастер: {master_label}\n"
            f"Дата: {texts.date_long(day)}\n\nСвободные окна:")
    await show(cb, text, kb.times_kb(service["id"], callback_data.mst, day, list(slots)))


@router.callback_query(Slot.filter())
async def choose_slot(cb: CallbackQuery, callback_data: Slot, pool, salon):
    service = await db.get_service(pool, salon["id"], callback_data.svc)
    if not service:
        return await show(cb, "Эта услуга сейчас недоступна.", kb.back_main_kb())
    masters = await db.masters_for_service(pool, salon["id"], service["id"])
    by_id = {m["id"]: m for m in masters}
    if callback_data.mst != 0 and callback_data.mst not in by_id:
        return await show(cb, "Этот мастер сейчас недоступен.", kb.back_main_kb())
    day = datetime.strptime(callback_data.d, "%Y%m%d").date()
    starts = datetime.combine(day, datetime.strptime(callback_data.t, "%H%M").time(), tzinfo=booking.salon_tz(salon))
    if callback_data.mst == 0:
        price, master_label = service["price"], "Любой свободный"
    else:
        m = by_id[callback_data.mst]
        price, master_label = m["price"], m["name"]
    text = (
        "✅ <b>Подтверждение записи</b>\n\nПроверьте данные:\n\n"
        f"🏠 Салон: {salon['name']}\n"
        f"💇 Услуга: {service['name']}\n"
        f"👩 Мастер: {master_label}\n"
        f"📅 Дата: {texts.date_long(day)}\n"
        f"🕒 Время: {starts:%H:%M}\n"
        f"⏳ Продолжительность: {service['duration_min']} минут\n"
        f"💰 Стоимость: {texts.money(price, service['price_from'])}\n\nВсё верно?"
    )
    await show(cb, text, kb.confirm_kb(service["id"], callback_data.mst, callback_data.d, callback_data.t))


@router.callback_query(Ok.filter())
async def confirm(cb: CallbackQuery, callback_data: Ok, pool, salon, bot: Bot):
    await cb.answer("Сохраняем…")
    service = await db.get_service(pool, salon["id"], callback_data.svc)
    if not service:
        return await show(cb, "Эта услуга сейчас недоступна.", kb.back_main_kb())
    day = datetime.strptime(callback_data.d, "%Y%m%d").date()
    tz = booking.salon_tz(salon)
    starts = datetime.combine(day, datetime.strptime(callback_data.t, "%H%M").time(), tzinfo=tz)
    client = await db.upsert_client(pool, salon["id"], cb.from_user.id, cb.from_user.full_name)

    try:
        res = await booking.book(pool, salon, client, service, callback_data.mst, starts)
    except Exception:
        log.exception("booking failed")
        return await show(cb, "Не получилось записаться, попробуйте ещё раз.", kb.confirm_kb(
            service["id"], callback_data.mst, callback_data.d, callback_data.t))

    if res.status == "busy":
        slots = await booking.day_slots(pool, salon, service, [callback_data.mst] if callback_data.mst else
                                        [m["id"] for m in await db.masters_for_service(pool, salon["id"], service["id"])], day)
        return await show(
            cb, "К сожалению, это время уже занято. Пожалуйста, выберите другое свободное окно.",
            kb.times_kb(service["id"], callback_data.mst, day, list(slots)))
    if res.status == "invalid":
        return await show(cb, "Этот мастер сейчас недоступен.", kb.back_main_kb())

    # ok или duplicate (повторное нажатие): показываем одну и ту же запись, дубля не создаём
    appt = dict(res.appointment)
    appt["master_name"] = res.master_name
    text = ("🎉 <b>Вы успешно записаны!</b>\n\n" f"Ждём вас в {salon['name']}!\n\n"
            + texts.appt_card(appt, tz)
            + f"\n📍 Адрес: {salon['address']}\n\nМы напомним вам о предстоящем посещении.")
    await show(cb, text, kb.after_booking_kb(appt["id"], salon["map_url"]))

    if res.status == "ok" and ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"🆕 <b>Новая запись!</b>\n\nКлиент: {cb.from_user.full_name}\n" + texts.appt_card(appt, tz),
                parse_mode="HTML")
        except Exception:
            log.exception("admin notification failed")


# ---------- мои записи ----------

@router.callback_query(Menu.filter(F.to == "my"))
async def my_appointments(cb: CallbackQuery, pool, salon):
    tz = booking.salon_tz(salon)
    appts = await db.client_upcoming(pool, salon["id"], cb.from_user.id, booking.salon_now(salon))
    if not appts:
        return await show(cb, "📅 <b>Ваши записи</b>\n\nУ вас пока нет предстоящих записей.", kb.main_menu())
    await show(cb, "📅 <b>Ваши записи</b>\n\nВыберите запись:", kb.my_appointments_kb(appts, tz))


@router.callback_query(Appt.filter())
async def appointment_card(cb: CallbackQuery, callback_data: Appt, pool, salon):
    a = await db.get_client_appointment(pool, salon["id"], cb.from_user.id, callback_data.id)
    if not a or a["status"] not in ("booked", "confirmed"):
        return await show(cb, "Запись не найдена.", kb.back_main_kb())
    can = booking.can_self_cancel(salon, a["starts_at"])
    extra = "" if can else f"\n\nОтмена онлайн недоступна. Позвоните нам: {salon['phone']}"
    await show(cb, "📅 <b>Ваша запись</b>\n\n" + texts.appt_card(a, booking.salon_tz(salon)) + extra,
               kb.appt_kb(a["id"], can, salon["phone"]))


@router.callback_query(CancelAsk.filter())
async def cancel_ask(cb: CallbackQuery, callback_data: CancelAsk, pool, salon):
    a = await db.get_client_appointment(pool, salon["id"], cb.from_user.id, callback_data.id)
    if not a:
        return await show(cb, "Запись не найдена.", kb.back_main_kb())
    await show(cb, "Вы уверены, что хотите отменить запись?\n\n" + texts.appt_card(a, booking.salon_tz(salon)),
               kb.cancel_confirm_kb(a["id"]))


@router.callback_query(CancelYes.filter())
async def cancel_yes(cb: CallbackQuery, callback_data: CancelYes, pool, salon, bot: Bot):
    a = await db.get_client_appointment(pool, salon["id"], cb.from_user.id, callback_data.id)
    if not a:
        return await show(cb, "Запись не найдена.", kb.back_main_kb())
    if not booking.can_self_cancel(salon, a["starts_at"]):
        return await show(cb, f"Отмена онлайн уже недоступна. Позвоните нам: {salon['phone']}", kb.back_main_kb())
    done = await db.cancel_appointment(pool, salon["id"], a["id"])
    if done and ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"❌ <b>Запись отменена клиентом</b>\n\nКлиент: {cb.from_user.full_name}\n"
                + texts.appt_card(a, booking.salon_tz(salon)), parse_mode="HTML")
        except Exception:
            log.exception("admin notification failed")
    await show(cb, "✅ Запись отменена.", kb.main_menu())


# ---------- информационные разделы ----------

@router.callback_query(Menu.filter(F.to == "services"))
async def show_services(cb: CallbackQuery, pool, salon):
    services = await db.list_services(pool, salon["id"])
    lines = [f"💇 <b>Услуги {salon['name']}</b>\n"]
    for s in services:
        lines.append(f"<b>{s['name']}</b> — {texts.money(s['price'], s['price_from'])}, {s['duration_min']} мин")
    await show(cb, "\n".join(lines), kb.services_kb(services))


@router.callback_query(Menu.filter(F.to == "masters"))
async def show_masters(cb: CallbackQuery, pool, salon):
    masters = await db.list_masters(pool, salon["id"])
    lines = ["👩‍🎨 <b>Наши мастера</b>\n"]
    for m in masters:
        exp = f", опыт {m['experience_years']} лет" if m["experience_years"] else ""
        lines.append(f"<b>{m['name']}</b> — {m['specialization']}{exp}")
    await show(cb, "\n".join(lines), kb.back_main_kb())


@router.callback_query(Menu.filter(F.to == "contacts"))
async def show_contacts(cb: CallbackQuery, salon):
    text = (f"📍 <b>Где нас найти</b>\n\n🏠 {salon['name']}\n\nАдрес: {salon['address']}\n\n"
            f"Часы работы:\n{salon['hours_text']}\n\nТелефон: {salon['phone']}")
    await show(cb, text, kb.back_main_kb())


@router.callback_query(Menu.filter(F.to == "contact_admin"))
async def contact_admin(cb: CallbackQuery, salon):
    await show(cb, f"💬 Позвоните нам: {salon['phone']}\n\n(Чат с администратором появится в следующей версии.)",
               kb.back_main_kb())
