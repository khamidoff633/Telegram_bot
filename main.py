import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import web, ClientSession

from config import BOT_TOKEN
from database.db import init_db
from handlers.start import start_router
from handlers.downloader_handler import downloader_router
from handlers.voice_handler import voice_router
from handlers.admin_handler import admin_router
from handlers.payment_handler import payment_router

logging.basicConfig(level=logging.INFO)

# 1. Health-Check HTTP server for Render Free Web Service
async def handle_health_check(request):
    return web.Response(text="VoxMedia AI Bot is 24/7 Active!", status=200)

async def start_health_server():
    try:
        app = web.Application()
        app.router.add_get('/', handle_health_check)
        app.router.add_get('/health', handle_health_check)
        port = int(os.environ.get("PORT", 8080))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logging.info(f"🚀 Health Check HTTP server running on port {port}")
    except Exception as e:
        logging.warning(f"⚠️ Health Check HTTP server start skipped (port in use or local env): {e}")

# 2. Automatic Self-Ping Task (Har 10 daqiqada o'z-o'zini uyg'otib turuvchi avto-ping)
async def auto_self_ping():
    await asyncio.sleep(15)  # Server to'liq ishga tushishini kutish
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        logging.info(f"⚡ 24/7 Auto-Ping (0-Sleep) tizimi ishga tushdi: {render_url}")
        async with ClientSession() as session:
            while True:
                try:
                    async with session.get(f"{render_url}/health", timeout=10) as resp:
                        logging.info(f"🟢 Auto-ping status: {resp.status} (Server 24/7 faol!)")
                except Exception as e:
                    logging.warning(f"⚠️ Auto-ping ogohlantirish: {e}")
                await asyncio.sleep(600)  # Har 10 daqiqada ping yuboriladi

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN ko'rsatilmagan! .env faylni tekshiring.")

    # Ma'lumotlar bazasini ishga tushirish
    await init_db()
    print("✅ Ma'lumotlar bazasi tayyorlandi!")

    # Bot va Dispatcher obyektlarini yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Routerlarni biriktirish Tartibi (admin_router birinchi bo'lishi shart!)
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(payment_router)
    dp.include_router(downloader_router)
    dp.include_router(voice_router)

    print("🚀 Telegram Bot muvaffaqiyatli ishga tushdi va buyruqlarni kutmoqda...")

    # HTTP server, Auto-ping hamda Bot Polling-ni birgalikda ishga tushirish
    await start_health_server()
    asyncio.create_task(auto_self_ping())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot to'xtatildi!")
