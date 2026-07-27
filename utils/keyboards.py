import re
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import REQUIRED_CHANNEL

def get_main_reply_kb():
    keyboard = [
        [
            KeyboardButton(text="🎬 Media Yuklash"),
            KeyboardButton(text="🎙️ Voice Matnga")
        ],
        [
            KeyboardButton(text="👑 VIP Status"),
            KeyboardButton(text="🔗 Referal Taklif")
        ],
        [
            KeyboardButton(text="📊 Mening Limitlarim"),
            KeyboardButton(text="ℹ️ Yordam")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_channel_sub_kb():
    channel_url = f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}"
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Kanalga a'zo bo'lish", url=channel_url)
    builder.button(text="✅ A'zo bo'ldim (Tekshirish)", callback_data="check_subscription")
    builder.adjust(1)
    return builder.as_markup()

def get_subscribe_inline_kb(url: str = None):
    builder = InlineKeyboardBuilder()
    if url:
        # Telegram callback_data maximum 64 bytes limit fix
        match = re.search(r'/(?:reel|p|tv|shorts)/([A-Za-z0-9_-]+)', url)
        short_id = match.group(1)[:40] if match else url[:40]
        builder.button(text="🎵 Musiqa ajratib olish", callback_data=f"m_{short_id}")
    builder.button(text="💳 Obuna bo'lish (Cheksiz Limit)", callback_data="buy_vip")
    builder.adjust(1)
    return builder.as_markup()

def get_payment_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Click orqali to'lash (15,000 so'm)", callback_data="pay_click")
    builder.button(text="💳 Payme orqali to'lash (15,000 so'm)", callback_data="pay_payme")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="⬅️ Bosh menyuga qaytish")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

get_payment_inline_kb = get_payment_kb
