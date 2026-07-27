from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from config import REQUIRED_CHANNEL

ADMIN_TELEGRAM_ID = 1606900140

async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """
    Senior Developer Strict Channel Subscription Engine:
    1. Admin / Owner (1606900140) -> True (Cheksiz har doim o'tadi).
    2. Kanal a'zoligini Telegram API orqali qat'iy tekshiradi:
       - Foydalanuvchi kanalda bo'lsa (creator, administrator, member) -> True (O'tkazadi)
       - Foydalanuvchi kanalda bo'lmasa (left, kicked) yoki xato bo'lsa -> False (Obunani so'raydi)
    """
    if user_id == ADMIN_TELEGRAM_ID:
        return True

    if not REQUIRED_CHANNEL:
        return True

    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except Exception as e:
        print(f"⚠️ [Subscription Status] User {user_id} is NOT subscribed to {REQUIRED_CHANNEL}: {e}")
        return False
