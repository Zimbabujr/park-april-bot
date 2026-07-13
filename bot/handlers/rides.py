"""
Обработчики поездок
"""
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, and_, or_, desc

from bot.config import config
from bot.models.database import User, Ride, Booking, UserStatus, RideStatus, BookingStatus, async_session
from bot.keyboards.main import (
    main_menu_keyboard, seats_keyboard,
    price_type_keyboard, confirm_ride_keyboard, search_filters_keyboard,
    booking_request_keyboard, back_keyboard
)

router = Router()


class RideCreationStates(StatesGroup):
    """Состояния создания поездки"""
    waiting_from = State()
    waiting_to = State()
    waiting_date = State()
    waiting_time = State()
    waiting_seats = State()
    waiting_price = State()
    waiting_price_amount = State()
    waiting_comment = State()
    confirm = State()


class SearchStates(StatesGroup):
    """Состояния поиска"""
    waiting_direction = State()


@router.message(F.text == "🚗 Создать поездку")
async def create_ride_start(message: Message, state: FSMContext, user: User = None):
    """Начало создания поездки"""
    if not user or not user.is_driver:
        await message.answer("❌ Только пользователи с автомобилем могут создавать поездки. Если у вас есть авто, обновите данные в профиле.")
        return

    await message.answer(
        "🚗 <b>Создание поездки</b>\n\n"
        "Шаг 1 из 7: Введите <b>откуда</b> выезжаете:\n"
        "<i>Например: ул. Центральная, д. 15</i>"
    )
    await state.set_state(RideCreationStates.waiting_from)


@router.message(RideCreationStates.waiting_from)
async def process_from(message: Message, state: FSMContext):
    """Обработка точки отправления"""
    await state.update_data(from_address=message.text.strip())
    await message.answer(
        "🚗 <b>Создание поездки</b>\n\n"
        "Шаг 2 из 7: Введите <b>куда</b> едете:\n"
        "<i>Например: ТЦ Мега, ст. метро Теплый Стан</i>"
    )
    await state.set_state(RideCreationStates.waiting_to)


@router.message(RideCreationStates.waiting_to)
async def process_to(message: Message, state: FSMContext):
    """Обработка точки назначения"""
    await state.update_data(to_address=message.text.strip())
    await message.answer(
        "🚗 <b>Создание поездки</b>\n\n"
        "Шаг 3 из 7: Введите <b>дату</b> поездки (ДД.ММ.ГГГГ):\n"
        "<i>Например: 15.07.2026</i>"
    )
    await state.set_state(RideCreationStates.waiting_date)


@router.message(RideCreationStates.waiting_date)
async def process_date(message: Message, state: FSMContext):
    """Обработка даты"""
    try:
        date = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        if date.date() < datetime.now().date():
            await message.answer("❌ Дата не может быть в прошлом. Введите корректную дату:")
            return
        await state.update_data(departure_date=date)
        await message.answer(
            "🚗 <b>Создание поездки</b>\n\n"
            "Шаг 4 из 7: Введите <b>время</b> отправления (ЧЧ:ММ):\n"
            "<i>Например: 09:30</i>"
        )
        await state.set_state(RideCreationStates.waiting_time)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ:")


@router.message(RideCreationStates.waiting_time)
async def process_time(message: Message, state: FSMContext):
    """Обработка времени"""
    try:
        time_str = message.text.strip()
        hour, minute = map(int, time_str.split(":"))

        data = await state.get_data()
        date = data['departure_date']
        departure = datetime(date.year, date.month, date.day, hour, minute)

        if departure < datetime.now():
            await message.answer("❌ Время уже прошло. Введите корректное время:")
            return

        await state.update_data(departure_datetime=departure)
        await message.answer(
            "🚗 <b>Создание поездки</b>\n\n"
            "Шаг 5 из 7: Сколько <b>свободных мест</b>?",
            reply_markup=seats_keyboard()
        )
        await state.set_state(RideCreationStates.waiting_seats)
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ:")


@router.callback_query(F.data.startswith("seats_"))
async def process_seats(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора мест"""
    seats = int(callback.data.split("_")[1])
    await state.update_data(total_seats=seats, available_seats=seats)
    await callback.message.edit_text(
        "🚗 <b>Создание поездки</b>\n\n"
        "Шаг 6 из 7: Выберите тип цены:",
        reply_markup=price_type_keyboard()
    )
    await state.set_state(RideCreationStates.waiting_price)
    await callback.answer()


@router.callback_query(F.data == "price_negotiable")
async def price_negotiable(callback: CallbackQuery, state: FSMContext):
    """Договорная цена"""
    await state.update_data(price_type="negotiable", price_amount=None)
    await callback.message.edit_text(
        "🚗 <b>Создание поездки</b>\n\n"
        "Шаг 7 из 7: Добавьте <b>комментарий</b> (или отправьте \"-\" для пропуска):\n"
        "<i>Например: Заберу у подъезда, можно с багажом</i>"
    )
    await state.set_state(RideCreationStates.waiting_comment)
    await callback.answer()


@router.callback_query(F.data == "price_fixed")
async def price_fixed(callback: CallbackQuery, state: FSMContext):
    """Фиксированная цена"""
    await callback.message.edit_text(
        "🚗 <b>Создание поездки</b>\n\n"
        "Введите <b>стоимость</b> поездки (руб):\n"
        "<i>Например: 150</i>"
    )
    await state.set_state(RideCreationStates.waiting_price_amount)
    await callback.answer()


@router.message(RideCreationStates.waiting_price_amount)
async def process_price_amount(message: Message, state: FSMContext):
    """Обработка суммы"""
    try:
        amount = int(message.text.strip())
        if amount < 0 or amount > 10000:
            await message.answer("❌ Введите сумму от 0 до 10000 руб:")
            return
        await state.update_data(price_type="fixed", price_amount=amount)
        await message.answer(
            "🚗 <b>Создание поездки</b>\n\n"
            "Шаг 7 из 7: Добавьте <b>комментарий</b> (или отправьте \"-\" для пропуска):\n"
            "<i>Например: Заберу у подъезда, можно с багажом</i>"
        )
        await state.set_state(RideCreationStates.waiting_comment)
    except ValueError:
        await message.answer("❌ Введите число:")


@router.message(RideCreationStates.waiting_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обработка комментария"""
    comment = message.text.strip()
    if comment == "-":
        comment = None
    await state.update_data(comment=comment)

    # Показываем сводку
    data = await state.get_data()

    price_text = "Договорная" if data['price_type'] == "negotiable" else f"{data['price_amount']} руб."
    comment_text = f"\n💬 <b>Комментарий:</b> {data.get('comment')}" if data.get('comment') else ""

    summary = (
        "📋 <b>Проверьте данные поездки:</b>\n\n"
        f"📍 <b>Откуда:</b> {data['from_address']}\n"
        f"🏁 <b>Куда:</b> {data['to_address']}\n"
        f"📅 <b>Когда:</b> {data['departure_datetime'].strftime('%d.%m.%Y %H:%M')}\n"
        f"👥 <b>Мест:</b> {data['total_seats']}\n"
        f"💰 <b>Цена:</b> {price_text}"
        f"{comment_text}\n\n"
        "Всё верно?"
    )

    await message.answer(summary, reply_markup=confirm_ride_keyboard())
    await state.set_state(RideCreationStates.confirm)


@router.callback_query(F.data == "publish_ride")
async def publish_ride(callback: CallbackQuery, state: FSMContext, user: User = None):
    """Публикация поездки"""
    data = await state.get_data()

    async with async_session() as session:
        ride = Ride(
            driver_id=user.id,
            from_address=data['from_address'],
            to_address=data['to_address'],
            departure_date=data['departure_datetime'],
            total_seats=data['total_seats'],
            available_seats=data['total_seats'],
            price_type=data['price_type'],
            price_amount=data.get('price_amount'),
            comment=data.get('comment'),
            status=RideStatus.ACTIVE,
        )
        session.add(ride)
        await session.commit()
        await session.refresh(ride)

        # Публикуем в канал
        price_text = "Договорная" if ride.price_type == "negotiable" else f"{ride.price_amount} руб."
        comment_text = f"\n💬 {ride.comment}" if ride.comment else ""

        channel_text = (
            f"🚗 <b>Новая поездка в районе {config.DISTRICT_NAME}</b>\n\n"
            f"📍 <b>Откуда:</b> {ride.from_address}\n"
            f"🏁 <b>Куда:</b> {ride.to_address}\n"
            f"📅 <b>Когда:</b> {ride.departure_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"👥 <b>Свободных мест:</b> {ride.available_seats}/{ride.total_seats}\n"
            f"💰 <b>Цена:</b> {price_text}"
            f"{comment_text}\n\n"
            f"👤 <b>Водитель:</b> {user.full_name}\n"
            f"📱 <b>Контакт:</b> {user.phone}\n\n"
            f"📝 Для бронирования напишите боту."
        )

        try:
            channel_msg = await callback.bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=channel_text
            )
            ride.channel_message_id = channel_msg.message_id
            await session.commit()
        except Exception as e:
            print(f"Ошибка публикации в канал: {e}")

    await callback.message.edit_text(
        "✅ <b>Поездка опубликована!</b>\n\n"
        "Она доступна в канале района и в поиске бота.\n"
        "Вы получите уведомление, когда кто-то подаст заявку."
    )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_ride_creation")
async def cancel_ride_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания поездки"""
    await callback.message.edit_text("❌ Создание поездки отменено.")
    await state.clear()
    await callback.answer()


@router.message(F.text == "🔍 Найти поездку")
async def search_rides(message: Message, state: FSMContext):
    """Поиск поездок"""
    await message.answer(
        "🔍 <b>Поиск поездок</b>\n\n"
        "Выберите фильтр:",
        reply_markup=search_filters_keyboard()
    )


@router.callback_query(F.data == "search_today")
async def search_today(callback: CallbackQuery):
    """Поиск на сегодня"""
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    async with async_session() as session:
        result = await session.execute(
            select(Ride, User).join(User, Ride.driver_id == User.id).where(
                and_(
                    Ride.departure_date >= datetime.combine(today, datetime.min.time()),
                    Ride.departure_date < datetime.combine(tomorrow, datetime.min.time()),
                    Ride.status == RideStatus.ACTIVE,
                    Ride.available_seats > 0
                )
            ).order_by(Ride.departure_date)
        )
        rides = result.all()

    if not rides:
        await callback.message.edit_text(
            "😔 Сегодня нет доступных поездок.\n\n"
            "Попробуйте поискать на завтра или создайте свою заявку.",
            reply_markup=back_keyboard()
        )
        await callback.answer()
        return

    text = "🚗 <b>Поездки на сегодня:</b>\n\n"
    for ride, driver in rides:
        price_text = "Договорная" if ride.price_type == "negotiable" else f"{ride.price_amount} руб."
        text += (
            f"📍 {ride.from_address} → {ride.to_address}\n"
            f"🕐 {ride.departure_date.strftime('%H:%M')} | "
            f"👥 {ride.available_seats} мест | 💰 {price_text}\n"
            f"👤 {driver.full_name}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "search_tomorrow")
async def search_tomorrow(callback: CallbackQuery):
    """Поиск на завтра"""
    tomorrow = datetime.now().date() + timedelta(days=1)
    day_after = tomorrow + timedelta(days=1)

    async with async_session() as session:
        result = await session.execute(
            select(Ride, User).join(User, Ride.driver_id == User.id).where(
                and_(
                    Ride.departure_date >= datetime.combine(tomorrow, datetime.min.time()),
                    Ride.departure_date < datetime.combine(day_after, datetime.min.time()),
                    Ride.status == RideStatus.ACTIVE,
                    Ride.available_seats > 0
                )
            ).order_by(Ride.departure_date)
        )
        rides = result.all()

    if not rides:
        await callback.message.edit_text(
            "😔 Завтра нет доступных поездок.",
            reply_markup=back_keyboard()
        )
        await callback.answer()
        return

    text = "🚗 <b>Поездки на завтра:</b>\n\n"
    for ride, driver in rides:
        price_text = "Договорная" if ride.price_type == "negotiable" else f"{ride.price_amount} руб."
        text += (
            f"📍 {ride.from_address} → {ride.to_address}\n"
            f"🕐 {ride.departure_date.strftime('%H:%M')} | "
            f"👥 {ride.available_seats} мест | 💰 {price_text}\n"
            f"👤 {driver.full_name}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "search_week")
async def search_week(callback: CallbackQuery):
    """Поиск на неделю"""
    now = datetime.now()
    week_later = now + timedelta(days=7)

    async with async_session() as session:
        result = await session.execute(
            select(Ride, User).join(User, Ride.driver_id == User.id).where(
                and_(
                    Ride.departure_date >= now,
                    Ride.departure_date <= week_later,
                    Ride.status == RideStatus.ACTIVE,
                    Ride.available_seats > 0
                )
            ).order_by(Ride.departure_date)
        )
        rides = result.all()

    if not rides:
        await callback.message.edit_text(
            "😔 На ближайшую неделю нет поездок.",
            reply_markup=back_keyboard()
        )
        await callback.answer()
        return

    text = "🚗 <b>Поездки на неделю:</b>\n\n"
    for ride, driver in rides:
        price_text = "Договорная" if ride.price_type == "negotiable" else f"{ride.price_amount} руб."
        text += (
            f"📍 {ride.from_address} → {ride.to_address}\n"
            f"📅 {ride.departure_date.strftime('%d.%m %H:%M')} | "
            f"👥 {ride.available_seats} мест | 💰 {price_text}\n"
            f"👤 {driver.full_name}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "search_direction")
async def search_direction(callback: CallbackQuery, state: FSMContext):
    """Поиск по направлению"""
    await callback.message.edit_text(
        "🔍 <b>Поиск по направлению</b>\n\n"
        "Введите <b>куда</b> вы хотите поехать:\n"
        "<i>Например: ТЦ Мега, метро, работа</i>"
    )
    await state.set_state(SearchStates.waiting_direction)
    await callback.answer()


@router.message(SearchStates.waiting_direction)
async def process_direction_search(message: Message, state: FSMContext):
    """Обработка поиска по направлению"""
    direction = message.text.strip().lower()
    now = datetime.now()

    async with async_session() as session:
        result = await session.execute(
            select(Ride, User).join(User, Ride.driver_id == User.id).where(
                and_(
                    Ride.departure_date >= now,
                    Ride.status == RideStatus.ACTIVE,
                    Ride.available_seats > 0,
                    or_(
                        Ride.to_address.ilike(f"%{direction}%"),
                        Ride.from_address.ilike(f"%{direction}%")
                    )
                )
            ).order_by(Ride.departure_date)
        )
        rides = result.all()

    if not rides:
        await message.answer(
            f"😔 По направлению «{message.text}» ничего не найдено.\n\n"
            "Попробуйте другой запрос.",
            reply_markup=back_keyboard()
        )
        await state.clear()
        return

    text = f"🚗 <b>Результаты поиска «{message.text}»:</b>\n\n"
    for ride, driver in rides:
        price_text = "Договорная" if ride.price_type == "negotiable" else f"{ride.price_amount} руб."
        text += (
            f"📍 {ride.from_address} → {ride.to_address}\n"
            f"📅 {ride.departure_date.strftime('%d.%m %H:%M')} | "
            f"👥 {ride.available_seats} мест | 💰 {price_text}\n"
            f"👤 {driver.full_name}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await message.answer(text, reply_markup=back_keyboard())
    await state.clear()


@router.callback_query(F.data.startswith("book_ride_"))
async def book_ride(callback: CallbackQuery, user: User = None):
    """Подать заявку на поездку"""
    ride_id = int(callback.data.split("_")[2])

    async with async_session() as session:
        result = await session.execute(
            select(Ride).where(Ride.id == ride_id)
        )
        ride = result.scalar_one_or_none()

        if not ride or ride.status != RideStatus.ACTIVE or ride.available_seats <= 0:
            await callback.answer("❌ Поездка недоступна", show_alert=True)
            return

        # Проверяем, не подавал ли уже заявку
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.ride_id == ride_id,
                    Booking.passenger_id == user.id,
                    Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
                )
            )
        )
        if result.scalar_one_or_none():
            await callback.answer("❌ Вы уже подавали заявку на эту поездку", show_alert=True)
            return

        # Создаём заявку
        booking = Booking(
            ride_id=ride_id,
            passenger_id=user.id,
            seats_requested=1,
            status=BookingStatus.PENDING
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)

        # Уведомляем водителя
        driver_result = await session.execute(
            select(User).where(User.id == ride.driver_id)
        )
        driver = driver_result.scalar_one()

        try:
            await callback.bot.send_message(
                chat_id=driver.telegram_id,
                text=(
                    f"🙋 <b>Новая заявка на поездку!</b>\n\n"
                    f"📍 {ride.from_address} → {ride.to_address}\n"
                    f"📅 {ride.departure_date.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"👤 <b>Пассажир:</b> {user.full_name}\n"
                    f"📱 <b>Телефон:</b> {user.phone}\n\n"
                    f"Примите или отклоните заявку:"
                ),
                reply_markup=booking_request_keyboard(booking.id)
            )
        except Exception as e:
            print(f"Ошибка уведомления водителя: {e}")

    await callback.message.edit_text(
        "✅ <b>Заявка отправлена!</b>\n\n"
        "Водитель получил уведомление и скоро рассмотрит вашу заявку.\n"
        "Вы получите уведомление о решении."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("accept_booking_"))
async def accept_booking(callback: CallbackQuery):
    """Принять заявку"""
    booking_id = int(callback.data.split("_")[2])

    async with async_session() as session:
        result = await session.execute(
            select(Booking, Ride, User).join(Ride, Booking.ride_id == Ride.id).join(
                User, Booking.passenger_id == User.id
            ).where(Booking.id == booking_id)
        )
        booking, ride, passenger = result.first()

        if booking.status != BookingStatus.PENDING:
            await callback.answer("❌ Заявка уже обработана", show_alert=True)
            return

        if ride.available_seats <= 0:
            await callback.answer("❌ Нет свободных мест", show_alert=True)
            return

        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_at = datetime.utcnow()
        ride.available_seats -= 1

        if ride.available_seats == 0:
            ride.status = RideStatus.FULL

        await session.commit()

        # Уведомляем пассажира
        try:
            await callback.bot.send_message(
                chat_id=passenger.telegram_id,
                text=(
                    f"✅ <b>Ваша заявка принята!</b>\n\n"
                    f"🚗 <b>Поездка:</b> {ride.from_address} → {ride.to_address}\n"
                    f"📅 {ride.departure_date.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"👤 <b>Водитель:</b> {callback.from_user.full_name}\n"
                    f"📱 <b>Телефон водителя:</b> будет доступен перед поездкой\n\n"
                    f"📝 За день до поездки вы получите контакты водителя."
                )
            )
        except Exception as e:
            print(f"Ошибка уведомления пассажира: {e}")

    await callback.message.edit_text(
        "✅ <b>Заявка принята!</b>\n\n"
        "Пассажир получил уведомление.\n"
        "За день до поездки контакты станут доступны обеим сторонам."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reject_booking_"))
async def reject_booking(callback: CallbackQuery):
    """Отклонить заявку"""
    booking_id = int(callback.data.split("_")[2])

    async with async_session() as session:
        result = await session.execute(
            select(Booking, Ride, User).join(Ride, Booking.ride_id == Ride.id).join(
                User, Booking.passenger_id == User.id
            ).where(Booking.id == booking_id)
        )
        booking, ride, passenger = result.first()

        if booking.status != BookingStatus.PENDING:
            await callback.answer("❌ Заявка уже обработана", show_alert=True)
            return

        booking.status = BookingStatus.REJECTED
        await session.commit()

        # Уведомляем пассажира
        try:
            await callback.bot.send_message(
                chat_id=passenger.telegram_id,
                text=(
                    f"❌ <b>Ваша заявка отклонена</b>\n\n"
                    f"🚗 {ride.from_address} → {ride.to_address}\n"
                    f"📅 {ride.departure_date.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Попробуйте найти другую поездку."
                )
            )
        except Exception as e:
            print(f"Ошибка уведомления пассажира: {e}")

    await callback.message.edit_text("❌ Заявка отклонена.")
    await callback.answer()


@router.message(F.text == "📅 Мои поездки")
async def my_rides(message: Message, user: User = None):
    """Мои поездки"""
    now = datetime.now()

    async with async_session() as session:
        # Поездки водителя
        result = await session.execute(
            select(Ride).where(
                and_(
                    Ride.driver_id == user.id,
                    Ride.departure_date >= now - timedelta(days=1)
                )
            ).order_by(desc(Ride.departure_date))
        )
        driver_rides = result.scalars().all()

        # Поездки пассажира
        result = await session.execute(
            select(Ride, Booking).join(Booking, Ride.id == Booking.ride_id).where(
                and_(
                    Booking.passenger_id == user.id,
                    Ride.departure_date >= now - timedelta(days=1)
                )
            ).order_by(desc(Ride.departure_date))
        )
        passenger_rides = result.all()

    if not driver_rides and not passenger_rides:
        await message.answer(
            "📅 <b>У вас пока нет поездок.</b>\n\n"
            "Создайте поездку или найдите подходящую!"
        )
        return

    text = "📅 <b>Ваши поездки:</b>\n\n"

    if driver_rides:
        text += "🚗 <b>Как водитель:</b>\n"
        for ride in driver_rides:
            status_emoji = {"active": "🟢", "full": "🟡", "completed": "✅", "cancelled": "❌"}.get(
                ride.status.value, "⚪"
            )
            text += (
                f"{status_emoji} {ride.departure_date.strftime('%d.%m %H:%M')} | "
                f"{ride.from_address[:15]}... → {ride.to_address[:15]}...\n"
            )
        text += "\n"

    if passenger_rides:
        text += "🙋 <b>Как пассажир:</b>\n"
        for ride, booking in passenger_rides:
            status_emoji = {"pending": "⏳", "confirmed": "✅", "completed": "✅", "rejected": "❌", "cancelled": "❌"}.get(
                booking.status.value, "⚪"
            )
            text += (
                f"{status_emoji} {ride.departure_date.strftime('%d.%m %H:%M')} | "
                f"{ride.from_address[:15]}... → {ride.to_address[:15]}...\n"
            )

    await message.answer(text)


@router.message(F.text == "👤 Мой профиль")
async def my_profile(message: Message, user: User = None):
    """Мой профиль"""
    car_text = f"🚗 <b>Авто:</b> {user.car_info}" if user.has_car else "🚶 <b>Роль:</b> Пассажир"
    status_emoji = {"approved": "✅", "pending": "⏳", "blocked": "🚫"}.get(user.status.value, "⚪")

    text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"📛 <b>ФИО:</b> {user.full_name}\n"
        f"🏠 <b>Адрес:</b> {user.address}\n"
        f"📱 <b>Телефон:</b> {user.phone}\n"
        f"{car_text}\n"
        f"📊 <b>Статус:</b> {status_emoji} {user.status.value}\n"
        f"📅 <b>Регистрация:</b> {user.registered_at.strftime('%d.%m.%Y')}\n\n"
        f"📍 <b>Район:</b> {config.DISTRICT_NAME}"
    )

    await message.answer(text)


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, user: User = None):
    """Возврат в меню"""
    await callback.message.delete()
    await callback.message.answer(
        "🚗 <b>Главное меню</b>",
        reply_markup=main_menu_keyboard(
            is_driver=user.is_driver if user else False,
            is_admin=callback.from_user.id in config.ADMIN_IDS
        )
    )
    await callback.answer()