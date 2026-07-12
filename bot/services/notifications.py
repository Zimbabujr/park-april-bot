"""
Сервис уведомлений
"""
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select, and_

from bot.config import config
from bot.models.database import Ride, Booking, User, BookingStatus, RideStatus, async_session


async def notify_upcoming_rides(bot: Bot):
    """
    Уведомление о приближающихся поездках
    Запускать через APScheduler каждый час
    """
    now = datetime.utcnow()
    soon = now + timedelta(hours=24)

    async with async_session() as session:
        # Поездки через 24 часа
        result = await session.execute(
            select(Ride, Booking, User).join(
                Booking, Ride.id == Booking.ride_id
            ).join(
                User, Booking.passenger_id == User.id
            ).where(
                and_(
                    Ride.departure_date.between(now, soon),
                    Ride.status == RideStatus.ACTIVE,
                    Booking.status == BookingStatus.CONFIRMED
                )
            )
        )
        rides = result.all()

        for ride, booking, passenger in rides:
            try:
                await bot.send_message(
                    chat_id=passenger.telegram_id,
                    text=(
                        f"⏰ <b>Напоминание о поездке!</b>\n\n"
                        f"🚗 {ride.from_address} → {ride.to_address}\n"
                        f"📅 {ride.departure_date.strftime('%d.%m.%Y %H:%M')}\n\n"
                        f"👤 Водитель: {ride.driver.full_name}\n"
                        f"📱 Телефон: {ride.driver.phone}\n\n"
                        f"Хорошей поездки! 🚀"
                    )
                )
            except Exception as e:
                print(f"Ошибка уведомления пассажира: {e}")

        # Уведомляем водителей
        result = await session.execute(
            select(Ride, User).join(User, Ride.driver_id == User.id).where(
                and_(
                    Ride.departure_date.between(now, soon),
                    Ride.status == RideStatus.ACTIVE
                )
            )
        )
        driver_rides = result.all()

        for ride, driver in driver_rides:
            try:
                await bot.send_message(
                    chat_id=driver.telegram_id,
                    text=(
                        f"⏰ <b>Напоминание о поездке!</b>\n\n"
                        f"🚗 {ride.from_address} → {ride.to_address}\n"
                        f"📅 {ride.departure_date.strftime('%d.%m.%Y %H:%M')}\n"
                        f"👥 Забронировано мест: {ride.total_seats - ride.available_seats}/{ride.total_seats}\n\n"
                        f"Не забудьте про поездку! 🚗"
                    )
                )
            except Exception as e:
                print(f"Ошибка уведомления водителя: {e}")


async def archive_old_rides():
    """
    Архивация старых поездок
    """
    cutoff = datetime.utcnow() - timedelta(days=config.RIDE_ARCHIVE_DAYS)

    async with async_session() as session:
        result = await session.execute(
            select(Ride).where(
                and_(
                    Ride.departure_date < cutoff,
                    Ride.status.in_([RideStatus.ACTIVE, RideStatus.FULL])
                )
            )
        )
        old_rides = result.scalars().all()

        for ride in old_rides:
            ride.status = RideStatus.COMPLETED

        await session.commit()
