from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from database.db import get_or_create_user, get_user_limits_info
from services.subscription import check_user_subscription
from utils.keyboards import get_main_reply_kb, get_subscribe_inline_kb, get_channel_sub_kb
from config import REQUIRED_CHANNEL

start_router = Router()

MANDATORY_SUB_TEXT = (
    f"⚠️ <b>Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'ling!</b>\n\n"
    f"Botdan bepul va cheksiz foydalanish uchun quyidagi kanalga ulaning:\n"
    f"👉 <b>{REQUIRED_CHANNEL}</b>\n\n"
    f"<i>Kanalga a'zo bo'lgach, <b>\"✅ A'zo bo'ldim (Tekshirish)\"</b> tugmasini bosing!</i>"
)

@start_router.message(CommandStart())
async def cmd_start(message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    # Referal ID ajratish
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    # Foydalanuvchini bazaga qo'shish
    user = await get_or_create_user(telegram_id, username, full_name, referrer_id)

    # Majburiy obuna tekshiruvi (VIP va adminlardan tashqari)
    is_sub = await check_user_subscription(message.bot, telegram_id)
    if not is_sub and not user.is_vip:
        await message.answer(MANDATORY_SUB_TEXT, reply_markup=get_channel_sub_kb(), parse_mode="HTML")
        return

    welcome_text = (
        f"👋 <b>Assalomu alaykum, {full_name}!</b>\n\n"
        f"<b>VoxMedia AI</b> botiga xush kelibsiz! 🚀\n\n"
        f" Men sizga quyidagi xizmatlarni taqdim etaman:\n"
        f"🎬 <b>Media Yuklash:</b> Instagram Reels va YouTube videolarni bepul yuklab berish.\n"
        f"🎙️ <b>Voice Matnga:</b> Ovozli xabarlarni avtomatik matnga o'girish (Uz/Ru/En).\n"
        f"🎵 <b>Musiqa Ajratish:</b> Videolardagi musiqalarni MP3 ringtone qilib berish.\n\n"
        f"👇 <b>Boshlash uchun menyudan kerakli bo'limni tanlang:</b>"
    )
    await message.answer(welcome_text, reply_markup=get_main_reply_kb(), parse_mode="HTML")

@start_router.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    is_sub = await check_user_subscription(callback.bot, telegram_id)

    if is_sub:
        await callback.answer("✅ Rahmat! Kanalga a'zo bo'ldingiz.", show_alert=True)
        welcome_text = (
            f"✅ <b>Kanalga a'zo bo'lganingiz uchun rahmat!</b>\n\n"
            f"Endi botdan to'liq va bepul foydalanishingiz mumkin. 👇"
        )
        try:
            await callback.message.edit_text(welcome_text, parse_mode="HTML")
        except Exception:
            pass
        await callback.message.answer("👇 Kerakli bo'limni tanlang:", reply_markup=get_main_reply_kb())
    else:
        await callback.answer(f"❌ Siz hali {REQUIRED_CHANNEL} kanaliga a'zo bo'lmadingiz! Iltimos, avval kanalga a'zo bo'ling.", show_alert=True)

@start_router.message(F.text == "🎬 Media Yuklash")
async def btn_media_download(message: Message):
    if not await check_user_subscription(message.bot, message.from_user.id):
        await message.answer(MANDATORY_SUB_TEXT, reply_markup=get_channel_sub_kb(), parse_mode="HTML")
        return
    text = (
        "🎬 <b>Media Yuklash Bo'limi</b>\n\n"
        "Menga Instagram Reels yoki YouTube Shorts/Video silkasini yuboring.\n"
        "Men sizga videoni va uning musiqasini yuklab beraman! 🚀"
    )
    await message.answer(text, parse_mode="HTML")

@start_router.message(F.text == "🎙️ Voice Matnga")
async def btn_voice_to_text(message: Message):
    if not await check_user_subscription(message.bot, message.from_user.id):
        await message.answer(MANDATORY_SUB_TEXT, reply_markup=get_channel_sub_kb(), parse_mode="HTML")
        return
    text = (
        "🎙️ <b>Voice Matnga O'girish Bo'limi</b>\n\n"
        "Menga ixtiyoriy ovozli xabar (Voice note) yuboring.\n"
        "Google AI yordamida uni aniq matnga o'girib beraman! 📝"
    )
    await message.answer(text, parse_mode="HTML")

@start_router.message(F.text == "👑 VIP Status")
async def btn_vip_status(message: Message):
    text = (
        "👑 <b>VIP Status Imkoniyatlari:</b>\n\n"
        "✅ <b>Cheksiz</b> video yuklash\n"
        "✅ <b>Maksimal HD (1080p/4K)</b> sifat\n"
        "✅ <b>Cheksiz</b> ovozli xabarlarni matnga o'girish\n"
        "✅ Reklamalarsiz va cheklovlarsiz ishlash\n\n"
        "💰 <b>Narxi:</b> 15,000 so'm / oyiga"
    )
    await message.answer(text, reply_markup=get_subscribe_inline_kb(), parse_mode="HTML")

@start_router.message(F.text == "🔗 Referal Taklif")
async def btn_referral(message: Message):
    telegram_id = message.from_user.id
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={telegram_id}"
    
    text = (
        f"🔗 <b>Sizning Referal Havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 Do'stlaringizni taklif qiling va bepul limitlarga ega bo'ling!"
    )
    await message.answer(text, parse_mode="HTML")

@start_router.message(F.text == "📊 Mening Limitlarim")
async def btn_limits(message: Message):
    telegram_id = message.from_user.id
    info = await get_user_limits_info(telegram_id)

    if info['is_vip']:
        text = "👑 <b>Siz VIP statusga egasiz!</b>\n\nBarcha limitlar siz uchun CHEKSIZ!"
    else:
        text = (
            f"📊 <b>Sizning Hozirgi Limitlaringiz:</b>\n\n"
            f"🎬 Video yuklash: <b>{info['video_remains']} ta</b> bepul qoldi\n"
            f"🎙️ Ovozli matn: <b>{info['voice_remains']} ta</b> bepul qoldi\n\n"
            f"⏱️ Limitlar har 48 soatda avtomatik yangilanadi."
        )
    await message.answer(text, parse_mode="HTML")

@start_router.message(F.text == "ℹ️ Yordam")
@start_router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "ℹ️ <b>Yordam va Yo'riqnoma:</b>\n\n"
        "1. <b>Video yuklash:</b> Instagram yoki YouTube silkasini botga yuboring.\n"
        "2. <b>Ovozli matn:</b> Botga ovozli xabar (voice) yuboring.\n"
        "3. <b>Musiqa:</b> Video yuklanganda uning musiqasi avtomatik ajratib beriladi.\n\n"
        "👨‍💻 Muammo bo'lsa admin bilan bog'laning: @bakhridd1n_dev"
    )
    await message.answer(text, parse_mode="HTML")
