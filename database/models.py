from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    
    # VIP status (Obunachi yoki Owner)
    is_vip = Column(Boolean, default=False)
    vip_expires_at = Column(DateTime, nullable=True)

    # Video yuklash limiti
    video_count = Column(Integer, default=0)
    video_reset_at = Column(DateTime, default=datetime.utcnow)

    # Voice transkripsiya limiti
    voice_count = Column(Integer, default=0)
    voice_reset_at = Column(DateTime, default=datetime.utcnow)

    # Referal tizimi
    referred_by = Column(BigInteger, nullable=True)
    bonus_video_limit = Column(Integer, default=0)
    bonus_voice_limit = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.telegram_id} - @{self.username} (VIP: {self.is_vip})>"
