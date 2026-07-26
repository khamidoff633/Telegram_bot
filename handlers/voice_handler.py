import os
import html
from aiogram import Router, F
from aiogram.types import Message
from database.db import can_user_transcribe_voice, increment_voice_count
from services.whisper import transcribe_voice
from services.subscription import check_user_subscription
from utils.keyboards import get_subscribe_inline_kb, get_channel_sub_kb
from config import REQUIRED_CHANNEL

voice_router = Router()

MANDATORY_SUB_TEXT = (
    f"✨ <b>Xush kelibsiz!</b>\n\n"
    f"Botimizdan to'liq va bepul foydalanish uchun rasmiy kanalimizga a'zo bo'ling:\n\n"
    f"📢 <b>{REQUIRED_CHANNEL}</b>\n\n"
    f"<i>Kanalga a'zo bo'lgach, quyidagi <b>\"✅ A'zo bo'ldim (Tekshirish)\"</b> tugmasini bosing!</i>"
)

VOICE_DIR = "voice_downloads"
os.makedirs(VOICE_DIR, exist_ok=True)

@voice_router.message(F.voice | F.audio)
async def handle_voice_message(message: Message):
    telegram_id = message.from_user.id

    # 1. Limit tekshiruvi
    can_transcribe, remains, user = await can_user_transcribe_voice(telegram_id)

    # 2. Majburiy obuna tekshiruvi
    if not await check_user_subscription(message.bot, telegram_id) and not user.is_vip:
        await message.answer(MANDATORY_SUB_TEXT, reply_markup=get_channel_sub_kb(), parse_mode="HTML")
        return

    if not can_transcribe and not user.is_vip:
        alert_text = (
            "⚠️ <b>Ovozli xabarlarni matnga o'g'irish limitingiz tugadi!</b>\n\n"
            "48 soatdan keyin yana bepul foydalanishingiz mumkin.\n"
            "Cheksiz foydalanish uchun <b>Obuna bo'lish</b> tugmasini bosing!"
        )
        await message.answer(alert_text, reply_markup=get_subscribe_inline_kb(), parse_mode="HTML")
        return

    status_msg = await message.answer("🎙️ Ovozli xabar eshitilmoqda va matnga o'girilmoqda, iltimos kuting...")

    try:
        # Fayl ID va Telegram'dan yuklab olish
        file_obj = message.voice or message.audio
        file_info = await message.bot.get_file(file_obj.file_id)
        
        file_ext = ".ogg" if message.voice else ".mp3"
        file_path = os.path.join(VOICE_DIR, f"{file_obj.file_id}{file_ext}")

        await message.bot.download_file(file_info.file_path, destination=file_path)

        # Gemini STT orqali matnga o'girish
        transcribed_text = await transcribe_voice(file_path)

        # Temp faylni o'chirish
        if os.path.exists(file_path):
            os.remove(file_path)

        if transcribed_text:
            safe_text = html.escape(transcribed_text)
            response_text = (
                f"📝 <b>Ovozli xabar matni:</b>\n\n"
                f"<i>\"{safe_text}\"</i>"
            )
            await status_msg.edit_text(response_text, parse_mode="HTML")

            if not user.is_vip:
                await increment_voice_count(telegram_id)
        else:
            await status_msg.edit_text("⚠️ Ovozli xabarda hech qanday soz tushunilmadi yoki audio bo'sh.")

    except Exception as e:
        print(f"Voice Handler Error: {e}")
        await status_msg.edit_text("❌ Ovozli xabarni matnga o'girishda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
