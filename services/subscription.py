from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from config import REQUIRED_CHANNEL

async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """
    Senior Developer Smart Subscription Engine:
    - Bot kanalda Admin bo'lsa: A'zolikni 100% aniqlikda tekshiradi (member/creator/administrator).
    - Bot kanalda hali Admin qilinmagan bo'lsa (member list is inaccessible): Foydalanuvchini bloklab qo'ymaslik uchun o'tkazib yuboradi.
    """
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except TelegramBadRequest as e:
        err_msg = str(e).lower()
        if "member list is inaccessible" in err_msg or "chat not found" in err_msg:
            print(f"⚠️ [Subscription Warning] Bot '{REQUIRED_CHANNEL}' kanalida admin emas. A'zolik tekshiruvi o'tkazib yuborildi.")
            # Foydalanuvchini botdan foydalanishdan cheklab qo'ymaslik uchun True qaytaramiz
            return True
        return False
    except Exception as e:
        print(f"Subscription Check Unknown Exception for user {user_id}: {e}")
        return True
