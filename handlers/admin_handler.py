from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database.db import get_bot_stats, get_all_users_list, is_admin_user
from utils.keyboards import get_admin_keyboard

admin_router = Router()

@admin_router.message(Command("admin"))
@admin_router.message(F.text == "📊 Admin Statistika")
async def cmd_admin_stats(message: Message):
    if not is_admin_user(message.from_user.id, message.from_user.username):
        await message.answer("❌ Bu bo'lim faqat bot admini uchun moslangan!")
        return

    stats = await get_bot_stats()

    text = (
        f"👑 <b>Admin Boshqaruv Paneli</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {stats['total_users']} ta\n"
        f"🌟 <b>VIP obunachilar:</b> {stats['vip_users']} ta\n"
    )

    await message.answer(text, parse_mode="HTML")

@admin_router.message(F.text == "👥 Foydalanuvchilar Listi")
async def btn_admin_users_list(message: Message):
    if not is_admin_user(message.from_user.id, message.from_user.username):
        await message.answer("❌ Ruxsat yo'q!")
        return

    users = await get_all_users_list()
    if not users:
        await message.answer("ℹ️ Hali foydalanuvchilar yo'q.")
        return

    text_lines = ["👥 <b>So'nggi Foydalanuvchilar Ro'yxati:</b>\n"]
    for u in users[:25]:
        uname = f"@{u.username}" if u.username else "User"
        vip_tag = "👑 VIP" if u.is_vip else "🆓 Free"
        text_lines.append(f"• {u.full_name or 'Foydalanuvchi'} ({uname}) - ID: <code>{u.telegram_id}</code> | {vip_tag}")

    await message.answer("\n".join(text_lines), parse_mode="HTML")
