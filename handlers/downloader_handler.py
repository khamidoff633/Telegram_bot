import os
import re
import html
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from database.db import can_user_download_video, increment_video_count
from services.downloader import download_video
from services.music_extractor import (
    extract_audio_from_local_file, 
    extract_audio_from_url, 
    identify_original_song,
    download_full_original_song,
    download_full_song_by_title
)
from services.subscription import check_user_subscription
from utils.keyboards import get_subscribe_inline_kb, get_channel_sub_kb
from config import REQUIRED_CHANNEL

downloader_router = Router()

MANDATORY_SUB_TEXT = (
    f"⚠️ <b>Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'ling!</b>\n\n"
    f"Botdan bepul va cheksiz foydalanish uchun quyidagi kanalga ulaning:\n"
    f"👉 <b>{REQUIRED_CHANNEL}</b>\n\n"
    f"<i>Kanalga a'zo bo'lgach, <b>\"✅ A'zo bo'ldim (Tekshirish)\"</b> tugmasini bosing!</i>"
)

def clean_song_name(name: str) -> str:
    """Instagram usernames (Video by ...), UUID and format extensions cleanup"""
    if not name or "video by" in name.lower() or "instagram" in name.lower() or "voxmedia" in name.lower():
        return "Original Sound"
    cleaned = re.sub(r'_[a-f0-9]{8}\.(?:mp4|mp3|m4a)$', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r'\.(?:mp4|mp3|m4a)$', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def is_media_url_msg(message: Message) -> bool:
    if not message or not message.text:
        return False
    txt = message.text.lower()
    return any(d in txt for d in ['instagram.com', 'instagr.am', 'youtube.com', 'youtu.be'])

@downloader_router.message(is_media_url_msg)
async def handle_video_download(message: Message):
    telegram_id = message.from_user.id
    text = message.text.strip()

    url_match = re.search(r'https?://[^\s]+', text)
    url = url_match.group(0) if url_match else text

    # 1. Majburiy obuna tekshiruvi (Hamma foydalanuvchilar uchun strict majburiy)
    is_subscribed = await check_user_subscription(message.bot, telegram_id)
    if not is_subscribed:
        await message.answer(MANDATORY_SUB_TEXT, reply_markup=get_channel_sub_kb(), parse_mode="HTML")
        return

    # 2. Limit tekshiruvi
    can_download, remains, user = await can_user_download_video(telegram_id)

    if not can_download and not user.is_vip:
        alert_text = (
            "⚠️ <b>Limitingiz tugadi!</b>\n\n"
            "48 soatdan keyin yana bepul foydalanishingiz mumkin.\n"
            "Sifatli (1080p/4K HD) va cheksiz limit xohlasangiz <b>Obuna bo'lish</b> tugmasini bosing!"
        )
        await message.answer(alert_text, reply_markup=get_subscribe_inline_kb(), parse_mode="HTML")
        return

    status_msg = await message.answer("⏳ Video va uning to'liq (original) musiqasi yuklanmoqda, iltimos kuting...")

    try:
        # 1-Qadam: Videoni yuklash
        result = await download_video(url, is_vip=user.is_vip)
        file_path = result['file_path']
        raw_title = result.get('title', 'Media Video')
        safe_title = html.escape(clean_song_name(raw_title))

        if not os.path.exists(file_path):
            await status_msg.edit_text(
                "❌ <b>Videoni yuklab bo'lmadi.</b>\n\n"
                "Iltimos, silka ochiq (public) post ekanligini tekshiring yoki YouTube Shorts silkasini yuborib ko'ring!",
                parse_mode="HTML"
            )
            return

        video_file = FSInputFile(file_path)

        # Videoni caption yozuvlarisiz toza yuborish
        if user.is_vip:
            await message.answer_video(video=video_file, caption=None)
        else:
            await message.answer_video(
                video=video_file, 
                caption=None, 
                reply_markup=get_subscribe_inline_kb(url=url)
            )
            await increment_video_count(telegram_id)

        # 2-Qadam: AI & YouTube Engine yordamida musiqaning TO'LIQ (ORIGINAL 3+ MINUTE) MP3 versiyasini yuborish!
        try:
            temp_mp3 = extract_audio_from_local_file(file_path)
            audio_to_send = None
            final_title = safe_title
            final_artist = "VoxMedia AI"

            if temp_mp3 and os.path.exists(temp_mp3):
                # 1-Urinish: Gemini AI orqali aniqlash
                song_info = await identify_original_song(temp_mp3)
                if song_info:
                    artist = song_info['artist']
                    title = song_info['title']
                    full_song_data = await download_full_original_song(artist, title)
                    if full_song_data and os.path.exists(full_song_data['file_path']):
                        audio_to_send = full_song_data['file_path']
                        final_title = html.escape(full_song_data['title'])
                        final_artist = html.escape(full_song_data['performer'])

                # 2-Urinish: Nomi bo'yicha to'liq original MP3 treki qidirish
                if not audio_to_send or not os.path.exists(audio_to_send):
                    full_title_data = await download_full_song_by_title(raw_title)
                    if full_title_data and os.path.exists(full_title_data['file_path']):
                        audio_to_send = full_title_data['file_path']
                        final_title = html.escape(full_title_data['title'])
                        final_artist = html.escape(full_title_data['performer'])

            # 3-Zaxira: Kesilgan mp3
            if not audio_to_send or not os.path.exists(audio_to_send):
                audio_to_send = temp_mp3

            if audio_to_send and os.path.exists(audio_to_send):
                audio_file = FSInputFile(audio_to_send)
                await message.answer_audio(
                    audio=audio_file,
                    title=final_title,
                    performer=final_artist,
                    caption=None
                )

                if audio_to_send != file_path and os.path.exists(audio_to_send):
                    try:
                        os.remove(audio_to_send)
                    except Exception:
                        pass
                if temp_mp3 != file_path and os.path.exists(temp_mp3):
                    try:
                        os.remove(temp_mp3)
                    except Exception:
                        pass
        except Exception as audio_err:
            print(f"Auto Full Original Audio Extraction Error: {audio_err}")

        await status_msg.delete()

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    except Exception as e:
        print(f"Download Error: {e}")
        await status_msg.edit_text(
            "❌ <b>Videoni yuklab bo'lmadi.</b>\n\n"
            "Iltimos, silka ochiq (public) post ekanligini tekshiring yoki YouTube Shorts silkasini yuboring!",
            parse_mode="HTML"
        )

@downloader_router.message(F.text & ~F.text.startswith("/"))
async def handle_unknown_text(message: Message):
    telegram_id = message.from_user.id
    is_subscribed = await check_user_subscription(message.bot, telegram_id)
    if not is_subscribed:
        await message.answer(MANDATORY_SUB_TEXT, reply_markup=get_channel_sub_kb(), parse_mode="HTML")
        return

    text = (
        "💡 <b>Menga Instagram Reels yoki YouTube Shorts/Video silkasini yuboring.</b>\n\n"
        "Men sizga videoni va uning to'liq original musiqasini yuklab beraman! 🚀"
    )
    await message.answer(text, parse_mode="HTML")

@downloader_router.callback_query(F.data.startswith("music_"))
async def handle_extract_music(callback: CallbackQuery):
    url = callback.data.replace("music_", "", 1)
    await callback.answer("🎵 Musiqa ajratib olinmoqda...")
    status_msg = await callback.message.answer("⏳ Videodagi musiqa ajratib olinmoqda...")

    try:
        result = await extract_audio_from_url(url)
        file_path = result['file_path']
        raw_title = result.get('title', 'Original Sound')
        safe_title = html.escape(clean_song_name(raw_title))

        if os.path.exists(file_path):
            audio_file = FSInputFile(file_path)
            await callback.message.answer_audio(
                audio=audio_file,
                title=safe_title,
                performer="VoxMedia AI",
                caption=None
            )
            await status_msg.delete()
            os.remove(file_path)
        else:
            await status_msg.edit_text("❌ Audioga aylantirishda xatolik bo'ldi.")
    except Exception as e:
        print(f"Music Extract Error: {e}")
        await status_msg.edit_text("❌ Audioga aylantirishda xatolik yuz berdi.")
