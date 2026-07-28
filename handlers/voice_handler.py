import os
import html
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from database.db import can_user_transcribe_voice, increment_voice_count, is_admin_user
from services.whisper import transcribe_voice
from services.subscription import check_user_subscription
from utils.keyboards import get_subscribe_inline_kb, get_channel_sub_kb
from config import REQUIRED_CHANNEL, FREE_VOICE_LIMIT

voice_router = Router()

MANDATORY_SUB_TEXT = (
    f"⚠️ <b>Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'ling!</b>\n\n"
    f"Botdan bepul va cheksiz foydalanish uchun quyidagi kanalga ulaning:\n"
    f"👉 <b>{REQUIRED_CHANNEL}</b>\n\n"
    f"<i>Kanalga a'zo bo'lgach, <b>\"✅ A'zo bo'ldim (Tekshirish)\"</b> tugmasini bosing!</i>"
)

VOICE_DIR = "voice_downloads"
os.makedirs(VOICE_DIR, exist_ok=True)

async def send_transcription_results(message: Message, status_msg: Message, transcribed_text: str):
    """Barcha 1, 5, 10 va 20 minutlik audiolarning matnlarini Telegram chekloviga tushirmasdan bo'lib yuborish"""
    safe_text = html.escape(transcribed_text)
    header = "📝 <b>Ovozli xabar matni:</b>\n\n"
    
    # 1. Qisqa matnlar uchun (3500 belgigacha)
    if len(safe_text) <= 3500:
        response_text = f"{header}<i>\"{safe_text}\"</i>"
        await status_msg.edit_text(response_text, parse_mode="HTML")
        return

    # 2. Uzun matnlar uchun (5-20 minutlik audiolar): 3500 belgilik bo'laklarga ajratish
    chunks = []
    curr = safe_text
    while len(curr) > 3500:
        split_pos = curr.rfind(" ", 0, 3500)
        if split_pos == -1 or split_pos < 2500:
            split_pos = 3500
        chunks.append(curr[:split_pos].strip())
        curr = curr[split_pos:].strip()
    if curr:
        chunks.append(curr)

    # Birinchi bo'lakni status xabariga tahrirlash
    first_part = f"📝 <b>Ovozli xabar matni (1/{len(chunks)}-Qism):</b>\n\n<i>\"{chunks[0]}\"</i>"
    await status_msg.edit_text(first_part, parse_mode="HTML")

    # Qolgan bo'laklarni ketma-ket yuborish
    for idx, chunk in enumerate(chunks[1:], start=2):
        part_text = f"📝 <b>( {idx}/{len(chunks)}-Qism ):</b>\n\n<i>\"{chunk}\"</i>"
        await message.answer(part_text, parse_mode="HTML")

    # 3. Agar matn juda uzun bo'lsa (7000+ belgi), foydalanuvchiga to'liq .txt faylini ham taqdim etish
    if len(transcribed_text) > 7000:
        txt_path = os.path.join(VOICE_DIR, f"Transcript_{message.message_id}.txt")
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(transcribed_text)
            
            doc_file = FSInputFile(txt_path, filename="Ovozli_Matn_Transcript.txt")
            await message.answer_document(
                document=doc_file,
                caption="📄 <b>Uzun audio matnining to'liq fayli (.txt)</b>",
                parse_mode="HTML"
            )
        except Exception as doc_err:
            print(f"Doc export error: {doc_err}")
        finally:
            if os.path.exists(txt_path):
                try:
                    os.remove(txt_path)
                except Exception:
                    pass

@voice_router.message(F.voice | F.audio)
async def handle_voice_message(message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username

    is_admin = is_admin_user(telegram_id, username)

    # 1. Majburiy obuna tekshiruvi (oddiy foydalanuvchilar uchun)
    if not is_admin:
        if not await check_user_subscription(message.bot, telegram_id, username):
            await message.answer(MANDATORY_SUB_TEXT, reply_markup=get_channel_sub_kb(), parse_mode="HTML")
            return

    # 2. Limit tekshiruvi
    can_transcribe, remains, user = await can_user_transcribe_voice(telegram_id, username)

    if not can_transcribe and not is_admin and not user.is_vip:
        alert_text = (
            "⚠️ <b>Ovozli xabarlarni matnga o'g'irish limitingiz tugagan!</b>\n\n"
            f"Siz 48 soat ichidagi Bepul <b>{FREE_VOICE_LIMIT} ta ovozli xabar</b> limitidan foydalanib bo'ldingiz.\n"
            "48 soatdan keyin limit avtomatik yangilanadi.\n\n"
            " Cheksiz matnga o'girish uchun <b>Obuna Bo'lish</b> tugmasini bosing!"
        )
        await message.answer(alert_text, reply_markup=get_subscribe_inline_kb(), parse_mode="HTML")
        return

    status_msg = await message.answer("🎙️ Ovozli/Audio fayl tahlil qilinmoqda, iltimos kuting...")

    try:
        file_obj = message.voice or message.audio
        file_info = await message.bot.get_file(file_obj.file_id)
        
        file_ext = os.path.splitext(file_info.file_path)[1] if file_info and file_info.file_path else (".ogg" if message.voice else ".mp3")
        file_path = os.path.join(VOICE_DIR, f"{file_obj.file_id}{file_ext}")

        await message.bot.download_file(file_info.file_path, destination=file_path)

        transcribed_text = await transcribe_voice(file_path)

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        if transcribed_text:
            await send_transcription_results(message, status_msg, transcribed_text)

            if not is_admin and not user.is_vip:
                await increment_voice_count(telegram_id, username)
                _, updated_remains, updated_user = await can_user_transcribe_voice(telegram_id, username)
                if updated_user.voice_count >= FREE_VOICE_LIMIT:
                    limit_reached_text = (
                        f"⚠️ <b>Sizning bepul ovozli matn limitingiz tugadi ({FREE_VOICE_LIMIT}/{FREE_VOICE_LIMIT} ta foydalanildi)!</b>\n\n"
                        f"48 soatdan keyin limitlar avtomatik yangilanadi.\n"
                        f" Cheksiz matnga o'girish uchun <b>Obuna Bo'lish</b> tugmasini bosing!"
                    )
                    await message.answer(limit_reached_text, reply_markup=get_subscribe_inline_kb(), parse_mode="HTML")
        else:
            await status_msg.edit_text("⚠️ Ovozli xabarda hech qanday soz tushunilmadi yoki audio bo'sh.")

    except Exception as e:
        print(f"Voice Handler Error: {e}")
        try:
            await status_msg.edit_text("❌ Ovozli xabarni matnga o'girishda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
        except Exception:
            pass


