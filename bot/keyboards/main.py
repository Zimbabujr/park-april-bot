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

def create_ride_keyboard() -> InlineKeyboardMarkup:
    """Кнопка создания поездки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚗 Создать поездку", callback_data="create_ride")
    return builder.as_markup()


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
    builder.button(text="🔄 Изменить", callback_data="edit_ride")
    builder.button(text="❌ Отменить", callback_data="cancel_ride_creation")
    builder.adjust(1)
    return builder.as_markup()


def ride_actions_keyboard(ride_id: int, is_driver: bool = False, is_owner: bool = False) -> InlineKeyboardMarkup:
    """Действия с поездкой"""
    builder = InlineKeyboardBuilder()

    if not is_driver and not is_owner:
        builder.button(text="🙋 Подать заявку", callback_data=f"book_ride_{ride_id}")

    if is_owner:
        builder.button(text="✏️ Редактировать", callback_data=f"edit_ride_{ride_id}")
        builder.button(text="❌ Отменить поездку", callback_data=f"cancel_ride_{ride_id}")

    builder.button(text="📍 Показать на карте", callback_data=f"show_map_{ride_id}")
    builder.adjust(1)
    return builder.as_markup()


def booking_request_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения/отклонения заявки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"accept_booking_{booking_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_booking_{booking_id}")
    builder.adjust(2)
    return builder.as_markup()


def my_rides_keyboard(rides: list) -> InlineKeyboardMarkup:
    """Список моих поездок"""
    builder = InlineKeyboardBuilder()
    for ride in rides:
        status_emoji = {
            "active": "🟢",            "full": "🟡",
            "in_progress": "🔵",            "completed": "✅",
            "cancelled": "❌"
        }.get(ride.status.value, "⚪")

        date_str = ride.departure_date.strftime("%d.%m %H:%M")
        builder.button(
            text=f"{status_emoji} {date_str} → {ride.to_address[:20]}...",
            callback_data=f"my_ride_{ride.id}"
        )
    builder.adjust(1)
    return builder.as_markup()


def ride_detail_keyboard(ride_id: int, status: str) -> InlineKeyboardMarkup:
    """Детали поездки"""
    builder = InlineKeyboardBuilder()

    if status in ["active", "full"]:
        builder.button(text="❌ Отменить поездку", callback_data=f"cancel_ride_{ride_id}")
    elif status == "completed":
        builder.button(text="⭐ Оставить отзыв", callback_data=f"review_ride_{ride_id}")

    builder.button(text="📋 Список пассажиров", callback_data=f"passengers_{ride_id}")
    builder.button(text="⬅️ Назад", callback_data="back_to_my_rides")
    builder.adjust(1)
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
    builder.button(text="🚫 Заблокировать пользователя", callback_data=f"admin_block_{reported_id}_{report_id}")
    builder.button(text="⚠️ Предупреждение", callback_data=f"admin_warn_{reported_id}_{report_id}")
    builder.button(text="❌ Отклонить жалобу", callback_data=f"admin_reject_{report_id}")
    builder.button(text="📋 История пользователя", callback_data=f"admin_history_{reported_id}")
    builder.adjust(1)
    return builder.as_markup()


def admin_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Действия с пользователем"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚫 Заблокировать", callback_data=f"admin_block_user_{user_id}")
    builder.button(text="✅ Разблокировать", callback_data=f"admin_unblock_user_{user_id}")
    builder.button(text="📋 Жалобы на пользователя", callback_data=f"admin_user_reports_{user_id}")
    builder.adjust(1)
    return builder.as_markup()


# === ОТЗЫВЫ ===

def rating_keyboard(ride_id: int) -> InlineKeyboardMarkup:
    """Выбор рейтинга"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        stars = "⭐" * i
        builder.button(text=stars, callback_data=f"rate_{ride_id}_{i}")
    builder.adjust(5)
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
