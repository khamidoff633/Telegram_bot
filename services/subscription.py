import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from config import REQUIRED_CHANNEL
from database.db import is_admin_user

async def check_user_subscription(bot: Bot, user_id: int, username: str = None) -> bool:
    """
    Senior Developer Strict Subscription Engine:
    1. Admin (bakhridd1n_dev) -> True (Shartlarsiz har doim VIP va a'zolik talab qilinmaydi).
    2. Oddiy foydalanuvchilar:
       - Creator / Admin / Member -> True (Kanalga a'zo, botdan foydalansa bo'ladi)
       - Left / Kicked -> False (A'zo emas, darhol majburiy obuna oynasi bilan bloklanadi)
    """
    if is_admin_user(user_id, username):
        logging.info(f"👑 Admin user {user_id} (@{username}) bypassed subscription check.")
        return True

    if not REQUIRED_CHANNEL:
        logging.warning("⚠️ REQUIRED_CHANNEL is empty, subscription check bypassed.")
        return True

    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        is_sub = member.status in ["creator", "administrator", "member"]
        logging.info(f"🔍 Subscription Check for {user_id} on {REQUIRED_CHANNEL}: status='{member.status}', is_sub={is_sub}")
        return is_sub
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logging.warning(f"⚠️ Subscription Check error for user {user_id} on channel '{REQUIRED_CHANNEL}': {e}")
        return False
    except Exception as e:
        logging.error(f"❌ Subscription Check unexpected error for user {user_id}: {e}")
        return False

