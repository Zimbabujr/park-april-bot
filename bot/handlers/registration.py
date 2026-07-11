"""
Обработчики регистрации пользователей
"""
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import config
from bot.models.database import User, UserStatus, async_session
from bot.keyboards.main import (
    registration_start_keyboard, has_car_keyboard, 
    confirm_registration_keyboard, main_menu_keyboard
)

router = Router()


class RegistrationStates(StatesGroup):
    """Состояния регистрации"""
    waiting_full_name = State()
    waiting_address = State()
    waiting_phone = State()
    waiting_has_car = State()
    waiting_car_info = State()
    confirm = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if user:
            if user.status == UserStatus.APPROVED:
                await message.answer(
                    f"👋 С возвращением, {user.first_name}!

"
                    f"🚗 <b>Бот карпулинга района «{config.DISTRICT_NAME}»</b>
"
                    f"Найдите поездку или создайте свою!",
                    reply_markup=main_menu_keyboard(
                        is_driver=user.is_driver,
                        is_admin=message.from_user.id in config.ADMIN_IDS
                    )
                )
            elif user.status == UserStatus.PENDING:
                await message.answer(
                    "⏳ <b>Ваша заявка на регистрацию находится на рассмотрении.</b>

"
                    "Администратор проверит ваши данные и одобрит доступ.
"
                    "Вы получите уведомление, когда это произойдёт."
                )
            elif user.status == UserStatus.BLOCKED:
                await message.answer(
                    "🚫 <b>Ваш аккаунт заблокирован.</b>

"
                    "Обратитесь к администратору для выяснения причин."
                )
            return

    # Новый пользователь — начинаем регистрацию
    await message.answer(
        f"👋 <b>Добро пожаловать в бот карпулинга района «{config.DISTRICT_NAME}»!</b>

"
        f"🚗 Здесь жители района могут:
"
        f"• Находить попутчиков для поездок
"
        f"• Предлагать свои поездки (если есть авто)
"
        f"• Экономить время и деньги

"
        f"📍 <b>Район:</b> {config.DISTRICT_NAME}
"
        f"📍 <b>Координаты:</b> {config.DISTRICT_LAT}, {config.DISTRICT_LON}

"
        f"Для использования бота необходимо пройти регистрацию.
"
        f"Все данные конфиденциальны и видны только участникам поездок.",
        reply_markup=registration_start_keyboard()
    )


@router.callback_query(F.data == "register_start")
async def register_start(callback: CallbackQuery, state: FSMContext):
    """Начало регистрации"""
    await callback.message.edit_text(
        "📝 <b>Регистрация — Шаг 1 из 5</b>

"
        "Введите ваше <b>ФИО</b> (полностью):
"
        "<i>Например: Иванов Иван Иванович</i>"
    )
    await state.set_state(RegistrationStates.waiting_full_name)
    await callback.answer()


@router.message(RegistrationStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Обработка ФИО"""
    full_name = message.text.strip()

    if len(full_name) < 5 or len(full_name) > 200:
        await message.answer(
            "❌ ФИО должно быть от 5 до 200 символов.
"
            "Пожалуйста, введите корректное ФИО:"
        )
        return

    await state.update_data(full_name=full_name)
    await message.answer(
        "📝 <b>Регистрация — Шаг 2 из 5</b>

"
        "Введите ваш <b>адрес проживания</b> в районе:
"
        "<i>Например: ул. Центральная, д. 15, кв. 42</i>"
    )
    await state.set_state(RegistrationStates.waiting_address)


@router.message(RegistrationStates.waiting_address)
async def process_address(message: Message, state: FSMContext):
    """Обработка адреса"""
    address = message.text.strip()

    if len(address) < 5:
        await message.answer(
            "❌ Адрес слишком короткий.
"
            "Пожалуйста, введите полный адрес:"
        )
        return

    await state.update_data(address=address)
    await message.answer(
        "📝 <b>Регистрация — Шаг 3 из 5</b>

"
        "Введите ваш <b>контактный телефон</b>:
"
        "<i>Например: +7 (999) 123-45-67</i>"
    )
    await state.set_state(RegistrationStates.waiting_phone)


@router.message(RegistrationStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка телефона"""
    phone = message.text.strip()

    # Простая валидация телефона
    cleaned = "".join(c for c in phone if c.isdigit() or c in "+-")
    if len(cleaned) < 10:
        await message.answer(
            "❌ Некорректный номер телефона.
"
            "Пожалуйста, введите номер в формате +7 (XXX) XXX-XX-XX:"
        )
        return

    await state.update_data(phone=cleaned)
    await message.answer(
        "📝 <b>Регистрация — Шаг 4 из 5</b>

"
        "У вас есть автомобиль?",
        reply_markup=has_car_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_has_car)


@router.callback_query(F.data == "has_car_yes")
async def has_car_yes(callback: CallbackQuery, state: FSMContext):
    """Пользователь имеет авто"""
    await state.update_data(has_car=True)
    await callback.message.edit_text(
        "📝 <b>Регистрация — Шаг 5 из 5</b>

"
        "Введите информацию об автомобиле:
"
        "<i>Например: Kia Rio, белый, А123БВ77</i>"
    )
    await state.set_state(RegistrationStates.waiting_car_info)
    await callback.answer()


@router.callback_query(F.data == "has_car_no")
async def has_car_no(callback: CallbackQuery, state: FSMContext):
    """Пользователь без авто"""
    await state.update_data(has_car=False, car_info=None)
    await show_registration_summary(callback.message, state)
    await callback.answer()


@router.message(RegistrationStates.waiting_car_info)
async def process_car_info(message: Message, state: FSMContext):
    """Обработка информации об авто"""
    car_info = message.text.strip()

    if len(car_info) < 3:
        await message.answer(
            "❌ Информация об авто слишком короткая.
"
            "Введите марку, модель и цвет:"
        )
        return

    await state.update_data(car_info=car_info)
    await show_registration_summary(message, state)


async def show_registration_summary(message, state: FSMContext):
    """Показать сводку регистрации"""
    data = await state.get_data()

    car_text = f"🚗 <b>Авто:</b> {data['car_info']}" if data.get('has_car') else "🚶 <b>Роль:</b> Пассажир"

    summary = (
        "📋 <b>Проверьте ваши данные:</b>

"
        f"👤 <b>ФИО:</b> {data['full_name']}
"
        f"🏠 <b>Адрес:</b> {data['address']}
"
        f"📱 <b>Телефон:</b> {data['phone']}
"
        f"{car_text}

"
        "Всё верно?"
    )

    await message.answer(summary, reply_markup=confirm_registration_keyboard())
    await state.set_state(RegistrationStates.confirm)


@router.callback_query(F.data == "confirm_reg")
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    """Подтверждение регистрации"""
    data = await state.get_data()

    async with async_session() as session:
        # Проверяем, не зарегистрирован ли уже
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        if result.scalar_one_or_none():
            await callback.answer("Вы уже зарегистрированы!", show_alert=True)
            await state.clear()
            return

        # Создаём пользователя
        user = User(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name or data['full_name'].split()[0],
            last_name=callback.from_user.last_name,
            full_name=data['full_name'],
            address=data['address'],
            phone=data['phone'],
            has_car=data.get('has_car', False),
            car_info=data.get('car_info'),
            is_driver=data.get('has_car', False),
            status=UserStatus.PENDING,
        )

        session.add(user)
        await session.commit()

    await callback.message.edit_text(
        "✅ <b>Регистрация завершена!</b>

"
        "Ваша заявка отправлена на проверку администратору.
"
        "После одобрения вы сможете пользоваться всеми функциями бота.

"
        "⏳ Обычно проверка занимает не более 24 часов."
    )

    # Уведомляем админов о новой регистрации
    # (реализуется в отдельном сервисе)

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "edit_reg")
async def edit_registration(callback: CallbackQuery, state: FSMContext):
    """Редактирование регистрации"""
    await callback.message.edit_text(
        "📝 <b>Регистрация — Шаг 1 из 5</b>

"
        "Введите ваше <b>ФИО</b> (полностью):
"
        "<i>Например: Иванов Иван Иванович</i>"
    )
    await state.set_state(RegistrationStates.waiting_full_name)
    await callback.answer()
