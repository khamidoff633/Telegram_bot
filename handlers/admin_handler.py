from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from config import ADMIN_USERNAME
from database.db import get_bot_stats
from utils.keyboards import get_admin_keyboard

admin_router = Router()

def is_admin(username: str) -> bool:
    if not username:
        return False
    return username.lower().lstrip('@') == ADMIN_USERNAME.lower()

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.username):
        await message.answer("❌ Bu buyruq faqat bot admini uchun moslangan!")
        return

    stats = await get_bot_stats()

    text = (
        f"👑 **Admin Boshqaruv Paneli** (@{ADMIN_USERNAME})\n\n"
        f"👥 Jami foydalanuvchilar: **{stats['total_users']} ta**\n"
        f"🌟 VIP obunachilar: **{stats['vip_users']} ta**\n"
    )

    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@admin_router.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.username):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    stats = await get_bot_stats()
    text = (
        f"📊 **Bot Statistikasi:**\n\n"
        f"👤 Barcha foydalanuvchilar: {stats['total_users']}\n"
        f"👑 VIP obunachilar: {stats['vip_users']}"
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()
