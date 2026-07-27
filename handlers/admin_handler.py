from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database.db import get_bot_stats, get_all_users_list, get_vip_users_list, is_admin_user
from utils.keyboards import get_admin_keyboard, get_main_reply_kb

admin_router = Router()

@admin_router.message(Command("admin"))
@admin_router.message(F.text == "📊 Admin Statistika")
async def cmd_admin_stats(message: Message):
    if not is_admin_user(message.from_user.id, message.from_user.username):
        await message.answer("❌ Bu bo'lim faqat bot admini uchun moslangan!", reply_markup=get_main_reply_kb(is_admin=False))
        return

    stats = await get_bot_stats()

    text = (
        f"👑 <b>Admin Dashboard & Statistika</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {stats['total_users']} ta\n"
        f"🌟 <b>VIP (To'lov qilgan) obunachilar:</b> {stats['vip_users']} ta\n"
    )

    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")

@admin_router.message(F.text == "👥 Barcha Foydalanuvchilar")
@admin_router.message(F.text == "👥 Foydalanuvchilar Listi")
async def btn_admin_users_list(message: Message):
    if not is_admin_user(message.from_user.id, message.from_user.username):
        await message.answer("❌ Ruxsat yo'q!", reply_markup=get_main_reply_kb(is_admin=False))
        return

    users = await get_all_users_list()
    if not users:
        await message.answer("ℹ️ Hali foydalanuvchilar yo'q.")
        return

    text_lines = ["👥 <b>So'nggi Foydalanuvchilar Ro'yxati:</b>\n"]
    for u in users[:30]:
        uname = f"@{u.username}" if u.username else "No Username"
        vip_tag = "👑 VIP" if u.is_vip else "🆓 Free"
        text_lines.append(f"• <b>{u.full_name or 'Foydalanuvchi'}</b> ({uname}) | ID: <code>{u.telegram_id}</code> | {vip_tag}")

    await message.answer("\n".join(text_lines), parse_mode="HTML")

@admin_router.message(F.text == "👑 VIP To'lov Qilganlar")
async def btn_admin_vip_users_list(message: Message):
    if not is_admin_user(message.from_user.id, message.from_user.username):
        await message.answer("❌ Ruxsat yo'q!", reply_markup=get_main_reply_kb(is_admin=False))
        return

    vip_users = await get_vip_users_list()
    if not vip_users:
        await message.answer("ℹ️ Hali pullik VIP obuna sotib olgan foydalanuvchilar yo'q.")
        return

    text_lines = ["👑 <b>VIP Obuna (To'lov Qilgan) Foydalanuvchilar Ro'yxati:</b>\n"]
    for u in vip_users[:30]:
        uname = f"@{u.username}" if u.username else "No Username"
        date_str = u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "Aktiv"
        text_lines.append(f"• <b>{u.full_name or 'Foydalanuvchi'}</b> ({uname}) | ID: <code>{u.telegram_id}</code> | 🟢 <b>VIP Faol</b> ({date_str})")

    await message.answer("\n".join(text_lines), parse_mode="HTML")

@admin_router.message(F.text == "⬅️ Bosh menyuga qaytish")
async def btn_back_to_main(message: Message):
    is_admin = is_admin_user(message.from_user.id, message.from_user.username)
    await message.answer("👇 Kerakli bo'limni tanlang:", reply_markup=get_main_reply_kb(is_admin=is_admin))

