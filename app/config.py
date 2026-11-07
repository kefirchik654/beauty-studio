import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/salonbot")
# Режим разработки: один бот = один салон. Для SaaS салон определяется по боту (см. README).
SALON_ID = int(os.environ.get("SALON_ID", "1"))
# Куда слать уведомления о новых записях (Telegram ID администратора), необязательно
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"]) if os.environ.get("ADMIN_CHAT_ID") else None
