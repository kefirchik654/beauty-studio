
import asyncio
import os

import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
SALON_ID = int(os.getenv("SALON_ID", "1"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def get_db():
    return await asyncpg.connect(DATABASE_URL)


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Добро пожаловать в BEAUTY STUDIO!\n\n"
        "Я помогу записаться к нашим мастерам.\n\n"
        "Команды:\n"
        "/services — список услуг\n"
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


async def main():
    if not BOT_TOKEN or not DATABASE_URL:
        raise RuntimeError(
            "Укажи BOT_TOKEN и DATABASE_URL в переменных окружения"
        )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
