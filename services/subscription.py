from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from config import REQUIRED_CHANNEL
from database.db import is_admin_user

async def check_user_subscription(bot: Bot, user_id: int, username: str = None) -> bool:
    """
    Senior Developer Strict Subscription Engine:
    1. Admin (bakhriddin03_05 / bakhridd1n_dev) -> True (Shartlarsiz har doim VIP va a'zolik talab qilinmaydi).
    2. Oddiy foydalanuvchilar:
       - Creator / Admin / Member -> True (Kanalga a'zo, botdan foydalansa bo'ladi)
       - Left / Kicked -> False (A'zo emas, darhol majburiy obuna oynasi bilan bloklanadi)
    """
    if is_admin_user(user_id, username):
        return True

    if not REQUIRED_CHANNEL:
        return True

    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        err_msg = str(e).lower()
        print(f"⚠️ Subscription Check warning for user {user_id}: {err_msg}")
        return False
    except Exception as e:
        print(f"Subscription Check Exception for user {user_id}: {e}")
        return False
