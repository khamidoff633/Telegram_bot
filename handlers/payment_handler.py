from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery, Message
from config import PAYME_PROVIDER_TOKEN, CLICK_PROVIDER_TOKEN, MONTHLY_SUB_PRICE
from database.db import activate_vip
from utils.keyboards import get_payment_inline_kb

payment_router = Router()

@payment_router.callback_query(F.data == "buy_vip")
async def process_buy_vip(callback: CallbackQuery):
    text = (
        "👑 **VIP Obuna Afzalliklari:**\n\n"
        "✅ Cheksiz video yuklashlar (No limit)\n"
        "✅ Videolarni maksimal **1080p / 4K HD** sifatda yuklash\n"
        "✅ Cheksiz voice transkripsiya (matnga o'girish)\n"
        "✅ Reklama va ogohlantirishlarsiz tezkor ishlov berish\n\n"
        "💰 Narxi: **25,000 so'm / oy**\n\n"
        "Quyidagi to'lov tizimlaridan birini tanlang:"
    )
    await callback.message.answer(text, reply_markup=get_payment_inline_kb(), parse_mode="Markdown")
    await callback.answer()

@payment_router.callback_query(F.data.in_({"pay_payme", "pay_click"}))
async def send_payment_invoice(callback: CallbackQuery, bot: Bot):
    provider = "Payme" if callback.data == "pay_payme" else "Click"
    provider_token = PAYME_PROVIDER_TOKEN if callback.data == "pay_payme" else CLICK_PROVIDER_TOKEN

    if not provider_token:
        # Provider token hali sozlanmagan bo'lsa test tartibi
        await callback.message.answer(
            f"ℹ️ **{provider} to'lov integratsiyasi:**\n\n"
            f"Bot admini hali `.env` faylida `{provider.upper()}_PROVIDER_TOKEN` to'lov tokenini sozlamagan.\n"
            f"To'lov tizimi ulanganidan so'ng ushbu tugma orqali to'lov avtomatik qabul qilinadi!",
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    prices = [LabeledPrice(label="VIP Obuna (1 oylik)", amount=MONTHLY_SUB_PRICE * 100)]  # tiyinda

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="VIP Obuna (1 Oy)",
        description="Cheksiz HD Video yuklash va Voice Transcribe xizmati",
        payload=f"vip_30days_{callback.from_user.id}",
        provider_token=provider_token,
        currency="UZS",
        prices=prices,
        start_parameter="vip-subscription"
    )
    await callback.answer()

@payment_router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@payment_router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    telegram_id = message.from_user.id
    await activate_vip(telegram_id, days=30)

    success_text = (
        "🎉 **Tabriklaymiz! Siz VIP Obunaga ega bo'ldingiz!** 👑\n\n"
        "Endi siz uchun barcha limitlar olib tashlandi, videolar 1080p/4K HD formatda va barcha xizmatlar cheksiz ishlaydi!"
    )
    await message.answer(success_text, parse_mode="Markdown")

@payment_router.callback_query(F.data == "close")
async def close_callback(callback: CallbackQuery):
    await callback.message.delete()
