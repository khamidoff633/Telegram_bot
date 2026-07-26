import os
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, update, func

from database.models import Base, User
from config import ADMIN_USERNAME, FREE_VIDEO_LIMIT, FREE_VOICE_LIMIT, RESET_LIMIT_HOURS

DB_PATH = "bot_database.sqlite"
engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_or_create_user(telegram_id: int, username: str = None, full_name: str = None, referred_by: int = None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        is_owner = (username and username.lower().lstrip('@') == ADMIN_USERNAME.lower())

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                is_vip=is_owner,
                referred_by=referred_by,
                video_reset_at=datetime.utcnow(),
                voice_reset_at=datetime.utcnow()
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Referal egasiga bonus berish
            if referred_by and referred_by != telegram_id:
                await add_referral_bonus(referred_by)
        else:
            # Username/Full name yoki Owner VIP statusini yangilash
            updated = False
            if user.username != username or user.full_name != full_name:
                user.username = username
                user.full_name = full_name
                updated = True
            if is_owner and not user.is_vip:
                user.is_vip = True
                updated = True
            if updated:
                await session.commit()

        return user

async def check_and_reset_limits(user: User, session: AsyncSession):
    now = datetime.utcnow()
    updated = False

    # Video reset
    if user.video_reset_at and now >= user.video_reset_at + timedelta(hours=RESET_LIMIT_HOURS):
        user.video_count = 0
        user.video_reset_at = now
        updated = True

    # Voice reset
    if user.voice_reset_at and now >= user.voice_reset_at + timedelta(hours=RESET_LIMIT_HOURS):
        user.voice_count = 0
        user.voice_reset_at = now
        updated = True

    # VIP muddati tugaganligini tekshirish
    if user.is_vip and user.vip_expires_at and now >= user.vip_expires_at:
        # Owner bo'lmasa VIPini bekor qilish
        is_owner = (user.username and user.username.lower().lstrip('@') == ADMIN_USERNAME.lower())
        if not is_owner:
            user.is_vip = False
            updated = True

    if updated:
        await session.commit()

async def can_user_download_video(telegram_id: int) -> tuple[bool, int, User]:
    """Qaytaradi: (mumkinmi, qolgan_limit, user_object)"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return False, 0, None

        await check_and_reset_limits(user, session)

        if user.is_vip:
            return True, 999999, user

        total_allowed = FREE_VIDEO_LIMIT + user.bonus_video_limit
        remains = total_allowed - user.video_count
        return (remains > 0), max(0, remains), user

async def increment_video_count(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user and not user.is_vip:
            user.video_count += 1
            await session.commit()

async def can_user_transcribe_voice(telegram_id: int) -> tuple[bool, int, User]:
    """Qaytaradi: (mumkinmi, qolgan_limit, user_object)"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return False, 0, None

        await check_and_reset_limits(user, session)

        if user.is_vip:
            return True, 999999, user

        total_allowed = FREE_VOICE_LIMIT + user.bonus_voice_limit
        remains = total_allowed - user.voice_count
        return (remains > 0), max(0, remains), user

async def increment_voice_count(telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user and not user.is_vip:
            user.voice_count += 1
            await session.commit()

async def get_user_limits_info(telegram_id: int) -> dict:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"is_vip": False, "video_remains": 0, "voice_remains": 0}

        await check_and_reset_limits(user, session)

        if user.is_vip:
            return {"is_vip": True, "video_remains": 999999, "voice_remains": 999999}

        video_remains = max(0, (FREE_VIDEO_LIMIT + user.bonus_video_limit) - user.video_count)
        voice_remains = max(0, (FREE_VOICE_LIMIT + user.bonus_voice_limit) - user.voice_count)
        return {
            "is_vip": False,
            "video_remains": video_remains,
            "voice_remains": voice_remains
        }

async def add_referral_bonus(referrer_telegram_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == referrer_telegram_id))
        referrer = result.scalar_one_or_none()
        if referrer:
            referrer.bonus_video_limit += 2  # +2 ta bonus video
            referrer.bonus_voice_limit += 2  # +2 ta bonus voice
            await session.commit()

async def activate_vip(telegram_id: int, days: int = 30):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_vip = True
            now = datetime.utcnow()
            if user.vip_expires_at and user.vip_expires_at > now:
                user.vip_expires_at += timedelta(days=days)
            else:
                user.vip_expires_at = now + timedelta(days=days)
            await session.commit()

async def get_bot_stats() -> dict:
    async with async_session() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        vip_users = (await session.execute(select(func.count(User.id)).where(User.is_vip == True))).scalar() or 0
        return {
            "total_users": total_users,
            "vip_users": vip_users
        }
