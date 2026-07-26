import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

from config import BOT_TOKEN
from database.db import init_db
from handlers.start import router as start_router
from handlers.downloader_handler import router as downloader_router
from handlers.voice_handler import router as voice_router
from handlers.admin_handler import router as admin_router
from handlers.payment_handler import router as payment_router

logging.basicConfig(level=logging.INFO)

# Lightweight Health Check Server for Render Free Web Service (Prevents Sleeping)
async def handle_health_check(request):
    return web.Response(text="VoxMedia AI Bot is 24/7 Active!", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    app.router.add_get('/health', handle_health_check)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🚀 Health Check HTTP server running on port {port}")

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN ko'rsatilmagan! .env faylni tekshiring.")

    # 1. Ma'lumotlar bazasini ishga tushirish
    await init_db()
    print("✅ Ma'lumotlar bazasi tayyorlandi!")

    # 2. Bot va Dispatcher obyektlarini yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 3. Handler (Router) larni ro'yxatdan o'tkazish
    dp.include_router(start_router)
    dp.include_router(downloader_router)
    dp.include_router(voice_router)
    dp.include_router(admin_router)
    dp.include_router(payment_router)

    print("🚀 Telegram Bot muvaffaqiyatli ishga tushdi va buyruqlarni kutmoqda...")

    # 4. Health-check HTTP server va Bot polling-ni birga ishga tushirish
    await start_health_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot to'xtatildi!")
