"""
Middleware авторизации и проверки блокировки
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy import select

from bot.models.database import User, UserStatus, async_session


class AuthMiddleware(BaseMiddleware):
    """
    Middleware проверки авторизации пользователя.
    Добавляет объект пользователя в data["user"] если он зарегистрирован.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        # Получаем telegram_id из события
        telegram_id = None
        if isinstance(event, Message):
            telegram_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            telegram_id = event.from_user.id

        if telegram_id:
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()
                data["user"] = user

        return await handler(event, data)


class BlockCheckMiddleware(BaseMiddleware):
    """
    Middleware проверки блокировки пользователя.
    Если пользователь заблокирован — отклоняет запрос.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        user = data.get("user")

        if user and user.status == UserStatus.BLOCKED:
            # Пользователь заблокирован
            text = (
                "🚫 <b>Доступ заблокирован</b>\n\n"
                "Ваш аккаунт был заблокирован за нарушение правил сообщества.\n"
                "Если вы считаете, что это ошибка, обратитесь к администратору."
            )

            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Ваш аккаунт заблокирован", show_alert=True)

            return None  # Прерываем обработку

        return await handler(event, data)