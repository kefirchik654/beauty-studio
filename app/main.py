
import asyncio
import os
import json

import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SALON_ID = int(os.getenv("SALON_ID", "1"))

WEBAPP_URL = "https://beauty-studio-blush.vercel.app"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def get_db():
    return await asyncpg.connect(DATABASE_URL)


@dp.message(Command("start"))
async def start(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="💎 Открыть BEAUTY STUDIO",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ],
        resize_keyboard=True,
    )

    await message.answer(
        "Добро пожаловать в BEAUTY STUDIO!\n\n"
        "Нажми кнопку ниже, чтобы выбрать услугу и записаться.",
        reply_markup=keyboard,
    )


@dp.message(Command("services"))
async def services(message: Message):
    conn = await get_db()

    try:
        rows = await conn.fetch(
            """
            SELECT name, price, duration_min, price_from
            FROM services
            WHERE salon_id = $1 AND is_active = true
            ORDER BY id
            """,
            SALON_ID,
        )

        if not rows:
            await message.answer("Услуги пока не добавлены.")
            return

        text = "Наши услуги:\n\n"

        for row in rows:
            price = f"от {row['price']}" if row["price_from"] else str(row["price"])
            text += (
                f"💇 {row['name']}\n"
                f"💰 Цена: {price} руб.\n"
                f"⏱ Длительность: {row['duration_min']} мин.\n\n"
            )

        await message.answer(text)

    finally:
        await conn.close()


@dp.message(lambda message: message.web_app_data is not None)
async def webapp_booking(message: Message):
    try:
        data = json.loads(message.web_app_data.data)

        name = data.get("name", "Не указано")
        phone = data.get("phone", "Не указан")
        service = data.get("service", "Не указана")
        price = data.get("price", "Не указана")
        duration = data.get("time", "Не указана")

        text = (
            "🆕 НОВАЯ ЗАЯВКА BEAUTY STUDIO\n\n"
            f"👤 Клиент: {name}\n"
            f"📞 Телефон: {phone}\n"
            f"💇 Услуга: {service}\n"
            f"💰 Цена: {price} ₽\n"
            f"⏱ Длительность: {duration} минут\n\n"
            "⚠️ Это заявка, время ещё не подтверждено."
        )

        if ADMIN_ID:
            await bot.send_message(ADMIN_ID, text)

        await message.answer(
            "✅ Заявка отправлена!\n"
            "Администратор свяжется с тобой для подтверждения."
        )

    except Exception:
        await message.answer("Не удалось отправить заявку. Попробуй ещё раз.")


async def main():
    if not BOT_TOKEN or not DATABASE_URL:
        raise RuntimeError(
            "Укажи BOT_TOKEN и DATABASE_URL в переменных окружения"
        )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
