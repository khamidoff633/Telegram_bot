import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database.db import init_db
from handlers.start import start_router
from handlers.downloader_handler import downloader_router
from handlers.voice_handler import voice_router
from handlers.payment_handler import payment_router
from handlers.admin_handler import admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

async def main():
    # 1. Ma'lumotlar bazasini ishga tushirish
    await init_db()
    print("✅ Ma'lumotlar bazasi tayyorlandi!")

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n❌ XATOLIK: BOT_TOKEN o'rnatilmagan!")
        print("Iltimos, `.env` faylini ochib, BotFather'dan olingan tokeningizni kiriting!\n")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Routerlarni ulash
    dp.include_router(start_router)
    dp.include_router(downloader_router)
    dp.include_router(voice_router)
    dp.include_router(payment_router)
    dp.include_router(admin_router)

    print("🚀 Telegram Bot muvaffaqiyatli ishga tushdi va buyruqlarni kutmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot to'xtatildi!")
