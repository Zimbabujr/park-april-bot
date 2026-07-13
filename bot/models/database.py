"""
Модели базы данных бота "Парк Апрель"
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, 
    DateTime, Boolean, Float, ForeignKey, Enum
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship

from bot.config import config

Base = declarative_base()


class UserStatus(str, PyEnum):
    """Статусы пользователя"""
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"


class RideStatus(str, PyEnum):
    """Статусы поездки"""
    ACTIVE = "active"
    FULL = "full"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BookingStatus(str, PyEnum):
    """Статусы бронирования"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ReportStatus(str, PyEnum):
    """Статусы жалобы"""
    NEW = "new"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)

    full_name = Column(String(200), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(20), nullable=False)
    has_car = Column(Boolean, default=False)
    car_info = Column(String(300), nullable=True)

    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    is_driver = Column(Boolean, default=False)

    registered_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    blocked_at = Column(DateTime, nullable=True)
    block_reason = Column(Text, nullable=True)

    # Связи
    rides = relationship("Ride", back_populates="driver", lazy="selectin")
    bookings = relationship("Booking", back_populates="passenger", lazy="selectin")
    reports_sent = relationship("Report", foreign_keys="Report.reporter_id", back_populates="reporter")
    reports_received = relationship("Report", foreign_keys="Report.reported_id", back_populates="reported")


class Ride(Base):
    """Модель поездки"""
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    from_address = Column(Text, nullable=False)
    from_lat = Column(Float, nullable=True)
    from_lon = Column(Float, nullable=True)
    to_address = Column(Text, nullable=False)
    to_lat = Column(Float, nullable=True)
    to_lon = Column(Float, nullable=True)

    departure_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    total_seats = Column(Integer, default=4)
    available_seats = Column(Integer, default=4)

    status = Column(Enum(RideStatus), default=RideStatus.ACTIVE, nullable=False)

    price_type = Column(String(20), default="negotiable")
    price_amount = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)

    channel_message_id = Column(BigInteger, nullable=True)

    driver = relationship("User", back_populates="rides")
    bookings = relationship("Booking", back_populates="ride", lazy="selectin")


class Booking(Base):
    """Модель бронирования"""
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    ride_id = Column(Integer, ForeignKey("rides.id"), nullable=False)
    passenger_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    seats_requested = Column(Integer, default=1)

    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    ride = relationship("Ride", back_populates="bookings")
    passenger = relationship("User", back_populates="bookings")


class Report(Base):
    """Модель жалобы"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reported_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ride_id = Column(Integer, ForeignKey("rides.id"), nullable=True)

    reason = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(Enum(ReportStatus), default=ReportStatus.NEW, nullable=False)

    admin_decision = Column(String(20), nullable=True)
    admin_comment = Column(Text, nullable=True)
    resolved_by = Column(BigInteger, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reports_sent")
    reported = relationship("User", foreign_keys=[reported_id], back_populates="reports_received")


class Review(Base):
    """Модель отзыва"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ride_id = Column(Integer, ForeignKey("rides.id"), nullable=False)

    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# === DATABASE ENGINE ===

# Для SQLite async
DATABASE_URL = config.DATABASE_URL
if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(DATABASE_URL, echo=config.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Получение сессии БД"""
    async with async_session() as session:
        yield session