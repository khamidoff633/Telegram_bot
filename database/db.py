import os
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, update, func

from database.models import Base, User
from config import ADMIN_USERNAME, FREE_VIDEO_LIMIT, FREE_VOICE_LIMIT, RESET_LIMIT_HOURS

DB_PATH = "bot_database.sqlite"
engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

ADMIN_USERNAMES = ["bakhriddin03_05", "bakhridd1n_dev"]

def is_admin_user(telegram_id: int = None, username: str = None) -> bool:
    if username:
        clean = username.lower().lstrip('@')
        if clean in ADMIN_USERNAMES:
            return True
    return False

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_or_create_user(telegram_id: int, username: str = None, full_name: str = None, referred_by: int = None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        is_owner = is_admin_user(telegram_id, username)

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

            if referred_by and referred_by != telegram_id:
                await add_referral_bonus(referred_by)
        else:
            updated = False
            if user.username != username or user.full_name != full_name:
                user.username = username
                user.full_name = full_name
                updated = True
            if is_owner and not user.is_vip:
                user.is_vip = True
                updated = True
            if not is_owner and user.is_vip:
                user.is_vip = False
                updated = True
            if updated:
                await session.commit()

        return user

async def check_and_reset_limits(user: User, session: AsyncSession):
    now = datetime.utcnow()
    updated = False

    if not user.video_reset_at or now >= user.video_reset_at + timedelta(hours=RESET_LIMIT_HOURS):
        user.video_count = 0
        user.video_reset_at = now
        updated = True

    if not user.voice_reset_at or now >= user.voice_reset_at + timedelta(hours=RESET_LIMIT_HOURS):
        user.voice_count = 0
        user.voice_reset_at = now
        updated = True

    if updated:
        await session.commit()

async def can_user_download_video(telegram_id: int, username: str = None) -> tuple[bool, int, User]:
    async with async_session() as session:
        user = await get_or_create_user(telegram_id, username)

        if is_admin_user(telegram_id, username) or user.is_vip:
            return True, 999999, user

        await check_and_reset_limits(user, session)
        remains = FREE_VIDEO_LIMIT - user.video_count
        return remains > 0, max(0, remains), user

async def increment_video_count(telegram_id: int, username: str = None):
    if is_admin_user(telegram_id, username):
        return
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user and not user.is_vip:
            user.video_count += 1
            await session.commit()

async def can_user_convert_voice(telegram_id: int, username: str = None) -> tuple[bool, int, User]:
    async with async_session() as session:
        user = await get_or_create_user(telegram_id, username)

        if is_admin_user(telegram_id, username) or user.is_vip:
            return True, 999999, user

        await check_and_reset_limits(user, session)
        remains = FREE_VOICE_LIMIT - user.voice_count
        return remains > 0, max(0, remains), user

can_user_transcribe_voice = can_user_convert_voice

async def increment_voice_count(telegram_id: int, username: str = None):
    if is_admin_user(telegram_id, username):
        return
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user and not user.is_vip:
            user.voice_count += 1
            await session.commit()

async def activate_vip(telegram_id: int, days: int = 30):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            user = await get_or_create_user(telegram_id)
        user.is_vip = True
        await session.commit()

async def add_referral_bonus(referrer_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == referrer_id))
        user = result.scalar_one_or_none()
        if user:
            user.referral_count += 1
            if user.video_count > 0:
                user.video_count -= 1
            await session.commit()

async def get_user_limits_info(telegram_id: int, username: str = None) -> dict:
    if is_admin_user(telegram_id, username):
        return {
            'is_vip': True,
            'video_remains': 'Cheksiz',
            'voice_remains': 'Cheksiz'
        }

    async with async_session() as session:
        user = await get_or_create_user(telegram_id, username)

        if user.is_vip:
            return {
                'is_vip': True,
                'video_remains': 'Cheksiz',
                'voice_remains': 'Cheksiz'
            }

        await check_and_reset_limits(user, session)
        v_remains = max(0, FREE_VIDEO_LIMIT - user.video_count)
        a_remains = max(0, FREE_VOICE_LIMIT - user.voice_count)

        return {
            'is_vip': False,
            'video_remains': v_remains,
            'voice_remains': a_remains
        }

async def get_bot_stats() -> dict:
    async with async_session() as session:
        total_result = await session.execute(select(func.count(User.id)))
        total_users = total_result.scalar() or 0

        vip_result = await session.execute(select(func.count(User.id)).where(User.is_vip == True))
        vip_users = vip_result.scalar() or 0

        return {
            'total_users': total_users,
            'vip_users': vip_users
        }

async def get_all_users_list() -> list:
    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.created_at.desc()).limit(50))
        return result.scalars().all()

async def get_vip_users_list() -> list:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.is_vip == True).order_by(User.created_at.desc()))
        return result.scalars().all()
