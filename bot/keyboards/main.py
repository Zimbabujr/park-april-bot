"""
Клавиатуры бота "Парк Апрель"
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.models.database import RideStatus, BookingStatus, UserStatus


# === ГЛАВНОЕ МЕНЮ ===

def main_menu_keyboard(is_driver: bool = False, is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Главное меню"""
    buttons = [
        [KeyboardButton(text="🔍 Найти поездку")],
        [KeyboardButton(text="📅 Мои поездки")],
        [KeyboardButton(text="👤 Мой профиль")],
    ]

    if is_driver:
        buttons.insert(1, [KeyboardButton(text="🚗 Создать поездку")])

    buttons.append([KeyboardButton(text="⚠️ Пожаловаться")])

    if is_admin:
        buttons.append([KeyboardButton(text="🛡️ Админ-панель")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню администратора"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Жалобы")],
            [KeyboardButton(text="👥 Пользователи")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="⬅️ Назад в меню")],
        ],
        resize_keyboard=True
    )


# === РЕГИСТРАЦИЯ ===

def registration_start_keyboard() -> InlineKeyboardMarkup:
    """Кнопка начала регистрации"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Начать регистрацию", callback_data="register_start")
    return builder.as_markup()


def has_car_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора наличия авто"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Да, есть авто", callback_data="has_car_yes")
    builder.button(text="🚶 Нет, я пассажир", callback_data="has_car_no")
    builder.adjust(1)
    return builder.as_markup()


def confirm_registration_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение регистрации"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_reg")
    builder.button(text="🔄 Изменить данные", callback_data="edit_reg")
    builder.adjust(1)
    return builder.as_markup()


# === ПОЕЗДКИ ===

def seats_keyboard() -> InlineKeyboardMarkup:
    """Выбор количества мест"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 5):
        builder.button(text=f"{i} место" if i == 1 else f"{i} места", callback_data=f"seats_{i}")
    builder.adjust(2)
    return builder.as_markup()


def price_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа цены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Договорная цена", callback_data="price_negotiable")
    builder.button(text="💰 Указать цену", callback_data="price_fixed")
    builder.adjust(1)
    return builder.as_markup()


def confirm_ride_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение создания поездки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать", callback_data="publish_ride")
    builder.button(text="❌ Отменить", callback_data="cancel_ride_creation")
    builder.adjust(1)
    return builder.as_markup()


def booking_request_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения/отклонения заявки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"accept_booking_{booking_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_booking_{booking_id}")
    builder.adjust(2)
    return builder.as_markup()


# === ПОИСК ===

def search_filters_keyboard() -> InlineKeyboardMarkup:
    """Фильтры поиска"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Сегодня", callback_data="search_today")
    builder.button(text="📅 Завтра", callback_data="search_tomorrow")
    builder.button(text="📅 На этой неделе", callback_data="search_week")
    builder.button(text="🔍 По направлению", callback_data="search_direction")
    builder.adjust(2)
    return builder.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    return builder.as_markup()


# === ЖАЛОБЫ ===

def report_reasons_keyboard() -> InlineKeyboardMarkup:
    """Причины жалобы"""
    builder = InlineKeyboardBuilder()
    reasons = [
        ("🚫 Не явился", "no_show"),
        ("📄 Ложная информация", "false_info"),
        ("😡 Грубое поведение", "rude"),
        ("⚠️ Проблемы с безопасностью", "safety"),
        ("📝 Другое", "other"),
    ]
    for text, data in reasons:
        builder.button(text=text, callback_data=f"report_reason_{data}")
    builder.adjust(1)
    return builder.as_markup()


def confirm_report_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение жалобы"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📤 Отправить жалобу", callback_data="send_report")
    builder.button(text="❌ Отменить", callback_data="cancel_report")
    builder.adjust(1)
    return builder.as_markup()


# === АДМИН ===

def admin_report_keyboard(report_id: int, reported_id: int) -> InlineKeyboardMarkup:
    """Действия админа с жалобой"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚫 Заблокировать", callback_data=f"admin_block_{reported_id}_{report_id}")
    builder.button(text="⚠️ Предупреждение", callback_data=f"admin_warn_{reported_id}_{report_id}")
    builder.button(text="❌ Отклонить жалобу", callback_data=f"admin_reject_{report_id}")
    builder.adjust(1)
    return builder.as_markup()