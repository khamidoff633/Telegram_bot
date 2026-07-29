import os
import re
import html
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from database.db import can_user_download_video, increment_video_count, is_admin_user, get_time_until_reset
from services.downloader import download_video, get_video_dimensions
from services.music_extractor import (
    extract_audio_from_local_file, 
    extract_audio_from_url, 
    identify_original_song,
    download_full_original_song,
    download_full_song_by_title
)
from services.subscription import check_user_subscription
from utils.keyboards import get_subscribe_inline_kb, get_channel_sub_kb
from config import REQUIRED_CHANNEL, FREE_VIDEO_LIMIT

downloader_router = Router()



MANDATORY_SUB_TEXT = (
    f"⚠️ <b>Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'ling!</b>\n\n"
    f"Botdan bepul va cheksiz foydalanish uchun quyidagi kanalga ulaning:\n"
    f"👉 <b>{REQUIRED_CHANNEL}</b>\n\n"
    f"<i>Kanalga a'zo bo'lgach, <b>\"✅ A'zo bo'ldim (Tekshirish)\"</b> tugmasini bosing!</i>"
)

MENU_BUTTON_TEXTS = {
    "🎬 Media Yuklash", "🎙️ Voice Matnga", "👑 VIP Status", "🔗 Referal Taklif",
    "📊 Mening Limitlarim", "ℹ️ Yordam", "👑 VIP To'lov Qilganlar",
    "👥 Barcha Foydalanuvchilar", "📊 Admin Statistika"
}

def clean_song_name(name: str) -> str:
    """Instagram usernames (Video by ...), UUID and format extensions cleanup"""
    if not name or "video by" in name.lower() or "instagram" in name.lower() or "voxmedia" in name.lower():
        return "Original Sound"
    cleaned = re.sub(r'_[a-f0-9]{8}\.(?:mp4|mp3|m4a)$', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r'\.(?:mp4|mp3|m4a)$', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def extract_song_query_from_metadata(result: dict) -> str:
    """Video description va metama'lumotlardan asl qo'shiq va muallif nomini professional ajratish"""
    if result.get('track') and result.get('artist'):
        return f"{result['artist']} {result['track']}"

    desc = result.get('description', '')
    if desc:
        credits_match = re.search(r'(?:Créditos|Credits|By|Artist):\s*([^,\n]+),\s*[“"]([^”"\n]+)[”"]', desc, re.IGNORECASE)
        if credits_match:
            artist = credits_match.group(1).strip()
            song = credits_match.group(2).strip()
            return f"{artist} {song}"

        lines = [l.strip() for l in desc.split('\n') if l.strip()]
        for line in lines[:5]:
            cleaned = re.sub(r'[^\w\s\-\ä\ö\ü\ß\á\é\í\ó\ú\ñ\à\è\ì\ò\ù]', ' ', line).strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)
            if len(cleaned) > 2 and not any(kw in cleaned.lower() for kw in ["video by", "follow", "http", "siga", "lanzada"]):
                hashtags = re.findall(r'#(\w+)', desc)
                artist_hint = ""
                for h in hashtags:
                    if len(h) > 3 and h.lower() not in ["music", "pop", "video", "reels", "viral", "trending", "fyp"]:
                        artist_hint = h
                        break
                if artist_hint and artist_hint.lower() not in cleaned.lower():
                    return f"{artist_hint} {cleaned}"
                return cleaned

    raw_title = result.get('title', '')
    if raw_title and not any(kw in raw_title.lower() for kw in ["video by", "instagram", "voxmedia"]):
        cleaned_title = re.sub(r'[\(\[\{].*?[\)\]\}]', '', raw_title).strip()
        if len(cleaned_title) > 2:
            return cleaned_title

    return ""

def is_media_url_msg(message: Message) -> bool:
    if not message or not message.text:
        return False
    txt = message.text.lower()
    return any(d in txt for d in ['instagram.com', 'instagr.am', 'youtube.com', 'youtu.be', 'tiktok.com', 'vt.tiktok.com'])

@downloader_router.message(is_media_url_msg)
async def handle_video_download(message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username
    text = message.text.strip()

    url_match = re.search(r'https?://[^\s]+', text)
    url = url_match.group(0) if url_match else text

    is_admin = is_admin_user(telegram_id, username)

    # 1. Majburiy obuna tekshiruvi (oddiy foydalanuvchilar uchun)
    if not is_admin:
        is_subscribed = await check_user_subscription(message.bot, telegram_id, username)
        if not is_subscribed:
            await message.answer(MANDATORY_SUB_TEXT, reply_markup=get_channel_sub_kb(), parse_mode="HTML")
            return

    # 2. Limit tekshiruvi (4-video bo'lsa darhol bloklanadi)
    can_download, remains, user = await can_user_download_video(telegram_id, username)

    if not can_download and not is_admin and not user.is_vip:
        time_left = get_time_until_reset(user.video_reset_at)
        alert_text = (
            "⚠️ <b>Sizning bepul video yuklash limitingiz tugagan!</b>\n\n"
            f"Siz 48 soat ichidagi Bepul <b>{FREE_VIDEO_LIMIT} ta video</b> limitidan foydalanib bo'ldingiz.\n"
            f"⏱️ Limit yangilanishiga <b>{time_left}</b> qoldi.\n\n"
            " Cheksiz va 1080p/4K HD formatda yuklash uchun <b>Obuna Bo'lish</b> tugmasini bosing!"
        )
        await message.answer(alert_text, reply_markup=get_subscribe_inline_kb(url=url), parse_mode="HTML")
        return

    status_msg = await message.answer("⏳ Video yuklanmoqda...")

    try:
        # User Role belgilash: Admin (1080p), VIP (720p-1080p), Free User (480p)

        user_role = "admin" if is_admin else ("vip" if user.is_vip else "user")

        # 1-Qadam: Videoni yuklash (Admin=1080p, VIP=720p-1080p, Free=480p)
        result = await download_video(url, user_role=user_role)
        file_path = result['file_path']
        raw_title = result.get('title', 'Media Video')
        meta_artist = result.get('artist')
        meta_track = result.get('track')
        safe_title = html.escape(clean_song_name(raw_title))

        if not os.path.exists(file_path):
            await status_msg.edit_text(
                "❌ <b>Videoni yuklab bo'lmadi.</b>\n\n"
                "Iltimos, silka ochiq (public) post ekanligini tekshiring yoki YouTube Shorts silkasini yuborib ko'ring!",
                parse_mode="HTML"
            )
            return

        video_file = FSInputFile(file_path)
        meta = get_video_dimensions(file_path)

        v_width = meta['width'] if meta.get('width', 0) > 0 else None
        v_height = meta['height'] if meta.get('height', 0) > 0 else None
        v_duration = meta['duration'] if meta.get('duration', 0) > 0 else None

        # Video caption yozuvi: Admin/VIP uchun toza, oddiy foydalanuvchiga sifat va obuna eslatmasi
        if is_admin or user.is_vip:
            video_caption = None
            video_kb = None
        else:
            video_caption = "✨ <i>Maksimal (720p / 1080p HD) va cheksiz yuklashlar uchun <b>Obuna Bo'lish</b> tugmasini bosing!</i>"
            video_kb = get_subscribe_inline_kb(url=url)

        try:
            await message.answer_video(
                video=video_file,
                caption=video_caption,
                reply_markup=video_kb,
                width=v_width,
                height=v_height,
                duration=v_duration,
                supports_streaming=True,
                parse_mode="HTML"
            )
        except Exception as vid_err:
            print(f"Answer video err: {vid_err}")
            await message.answer_video(
                video=video_file,
                caption=None,
                supports_streaming=True
            )


        if not is_admin and not user.is_vip:
            await increment_video_count(telegram_id, username)

        # 2-Qadam: Post Description va Metadata bo'yicha TO'LIQ (3+ MINUTE) MP3 treki yuklash
        try:
            temp_mp3 = extract_audio_from_local_file(file_path)
            audio_to_send = None
            final_title = safe_title
            final_artist = "VoxMedia AI"

            search_query = extract_song_query_from_metadata(result)
            if search_query:
                full_desc_song = await download_full_song_by_title(search_query)
                if full_desc_song and os.path.exists(full_desc_song['file_path']):
                    audio_to_send = full_desc_song['file_path']
                    final_title = html.escape(full_desc_song['title'])
                    final_artist = html.escape(full_desc_song['performer'])

            if not audio_to_send and meta_artist and meta_track:
                full_meta_song = await download_full_original_song(meta_artist, meta_track)
                if full_meta_song and os.path.exists(full_meta_song['file_path']):
                    audio_to_send = full_meta_song['file_path']
                    final_title = html.escape(full_meta_song['title'])
                    final_artist = html.escape(full_meta_song['performer'])

            if not audio_to_send and temp_mp3 and os.path.exists(temp_mp3):
                song_info = await identify_original_song(temp_mp3)
                if song_info:
                    artist = song_info['artist']
                    title = song_info['title']
                    full_song_data = await download_full_original_song(artist, title)
                    if full_song_data and os.path.exists(full_song_data['file_path']):
                        audio_to_send = full_song_data['file_path']
                        final_title = html.escape(full_song_data['title'])
                        final_artist = html.escape(full_song_data['performer'])

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

        try:
            await status_msg.delete()
        except Exception:
            pass

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        # 3-Qadam: 3-video yuborib bo'linganidan so'ng darhol limit tugagani va aniq qolgan soat haqida ogohlantirish yuborish
        if not is_admin and not user.is_vip:
            _, updated_remains, updated_user = await can_user_download_video(telegram_id, username)
            if updated_user.video_count >= FREE_VIDEO_LIMIT:
                time_left = get_time_until_reset(updated_user.video_reset_at)
                limit_reached_text = (
                    f"⚠️ <b>Sizning bepul video yuklash limitingiz tugadi ({FREE_VIDEO_LIMIT}/{FREE_VIDEO_LIMIT} ta foydalanildi)!</b>\n\n"
                    f"⏱️ Limit yangilanishiga <b>{time_left}</b> qoldi.\n\n"
                    f" Cheksiz va 1080p HD formatda yuklash uchun <b>Obuna Bo'lish</b> tugmasini bosing!"
                )
                await message.answer(limit_reached_text, reply_markup=get_subscribe_inline_kb(url=url), parse_mode="HTML")

    except Exception as e:
        print(f"Download Error: {e}")
        try:
            await status_msg.edit_text(
                "❌ <b>Videoni yuklab bo'lmadi.</b>\n\n"
                "Iltimos, silka ochiq (public) post ekanligini tekshiring yoki YouTube Shorts silkasini yuboring!",
                parse_mode="HTML"
            )
        except Exception:
            pass

@downloader_router.message(F.text & ~F.text.startswith("/") & ~F.text.in_(MENU_BUTTON_TEXTS))
async def handle_unknown_text(message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username
    is_admin = is_admin_user(telegram_id, username)
    if not is_admin:
        is_subscribed = await check_user_subscription(message.bot, telegram_id, username)
        if not is_subscribed:
            await message.answer(MANDATORY_SUB_TEXT, reply_markup=get_channel_sub_kb(), parse_mode="HTML")
            return

    text = (
        "💡 <b>Menga Instagram Reels, YouTube yoki TikTok silkasini yuboring.</b>\n\n"
        "Men sizga videoni va uning to'liq original musiqasini yuklab beraman! 🚀"
    )
    await message.answer(text, parse_mode="HTML")
