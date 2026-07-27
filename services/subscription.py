from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from config import REQUIRED_CHANNEL

async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """
    Senior Developer Smart Subscription Engine:
    1. Bot kanalda ADMIN bo'lsa:
       - Foydalanuvchi a'zo bo'lsa (creator, administrator, member) -> True
       - Foydalanuvchi a'zo bo'lmasa (left, kicked) -> False
    2. Bot kanalda hali ADMIN qilinmagan bo'lsa (member list is inaccessible / not enough rights):
       - Konsolga ogohlantirish yozadi va a'zo foydalanuvchilarni (jumladan kanal egasini) asossiz bloklab qo'ymaslik uchun True qaytaradi.
    """
    if not REQUIRED_CHANNEL:
        return True

    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        err_msg = str(e).lower()
        if any(kw in err_msg for kw in [
            "member list is inaccessible",
            "chat not found",
            "bot is not a member",
            "not enough rights",
            "user not found",
            "administrator rights",
        ]):
            print(f"⚠️ [Subscription Warning] Bot '{REQUIRED_CHANNEL}' kanalida ADMIN emas! Telegram A'zolikni aniqlay olmadi. Botni kanalda ADMIN qiling!")
            return True
        return False
    except Exception as e:
        print(f"Subscription Check Exception for user {user_id}: {e}")
        return True
