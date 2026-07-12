"""
Обработчики жалоб и блокировки
"""
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import config
from bot.models.database import User, Ride, Booking, Report, ReportStatus, UserStatus, async_session
from bot.keyboards.main import report_reasons_keyboard, confirm_report_keyboard, back_keyboard

router = Router()


class ReportStates(StatesGroup):
    """Состояния подачи жалобы"""
    waiting_user_id = State()
    waiting_reason = State()
    waiting_description = State()
    confirm = State()


# === ЖАЛОБА ===

@router.message(F.text == "⚠️ Пожаловаться")
async def report_start(message: Message, state: FSMContext):
    """Начало подачи жалобы"""
    await message.answer(
        "⚠️ <b>Подача жалобы</b>

"
        "Введите <b>ID пользователя</b> или <b>@username</b>, на которого хотите пожаловаться.
"
        "<i>ID можно узнать в профиле пользователя или в списке участников поездки.</i>

"
        "Если вы не знаете ID, опишите ситуацию, и мы поможем."
    )
    await state.set_state(ReportStates.waiting_user_id)


@router.message(ReportStates.waiting_user_id)
async def process_reported_user(message: Message, state: FSMContext):
    """Обработка ID пользователя"""
    text = message.text.strip()

    # Пытаемся найти пользователя
    async with async_session() as session:
        if text.startswith("@"):
            result = await session.execute(
                select(User).where(User.username == text[1:])
            )
        else:
            try:
                telegram_id = int(text)
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
            except ValueError:
                # Поиск по имени
                result = await session.execute(
                    select(User).where(User.full_name.ilike(f"%{text}%"))
                )

        reported_user = result.scalar_one_or_none()

        if not reported_user:
            await message.answer(
                "❌ Пользователь не найден.

"
                "Пожалуйста, введите корректный ID, @username или ФИО:
"
                "<i>Или отправьте "отмена" для выхода</i>"
            )
            return

        if reported_user.telegram_id == message.from_user.id:
            await message.answer("❌ Нельзя пожаловаться на самого себя!")
            return

    await state.update_data(reported_id=reported_user.id, reported_tg_id=reported_user.telegram_id)
    await message.answer(
        f"👤 <b>Жалоба на:</b> {reported_user.full_name}

"
        f"Выберите <b>причину</b> жалобы:",
        reply_markup=report_reasons_keyboard()
    )
    await state.set_state(ReportStates.waiting_reason)


@router.callback_query(F.data.startswith("report_reason_"))
async def process_report_reason(callback: CallbackQuery, state: FSMContext):
    """Обработка причины жалобы"""
    reason = callback.data.split("_")[2]
    reason_text = {
        "no_show": "Не явился на поездку",
        "false_info": "Ложная информация",
        "rude": "Грубое поведение",
        "safety": "Проблемы с безопасностью",
        "other": "Другое"
    }.get(reason, reason)

    await state.update_data(reason=reason, reason_text=reason_text)
    await callback.message.edit_text(
        f"⚠️ <b>Причина:</b> {reason_text}

"
        f"Опишите <b>ситуацию</b> подробно:
"
        f"<i>Что произошло, когда, какие нарушения</i>"
    )
    await state.set_state(ReportStates.waiting_description)
    await callback.answer()


@router.message(ReportStates.waiting_description)
async def process_report_description(message: Message, state: FSMContext):
    """Обработка описания жалобы"""
    description = message.text.strip()

    if len(description) < 10:
        await message.answer(
            "❌ Описание слишком короткое.
"
            "Пожалуйста, опишите ситуацию подробнее (минимум 10 символов):"
        )
        return

    await state.update_data(description=description)
    data = await state.get_data()

    summary = (
        "📋 <b>Проверьте жалобу:</b>

"
        f"👤 <b>На кого:</b> ID {data['reported_id']}
"
        f"📌 <b>Причина:</b> {data['reason_text']}
"
        f"📝 <b>Описание:</b> {description}

"
        "Отправить жалобу?"
    )

    await message.answer(summary, reply_markup=confirm_report_keyboard())
    await state.set_state(ReportStates.confirm)


@router.callback_query(F.data == "send_report")
async def send_report(callback: CallbackQuery, state: FSMContext, user: User = None):
    """Отправка жалобы"""
    data = await state.get_data()

    async with async_session() as session:
        report = Report(
            reporter_id=user.id,
            reported_id=data['reported_id'],
            reason=data['reason'],
            description=data['description'],
            status=ReportStatus.NEW
        )
        session.add(report)
        await session.commit()

        # Проверяем количество жалоб на пользователя
        result = await session.execute(
            select(func.count(Report.id)).where(
                and_(
                    Report.reported_id == data['reported_id'],
                    Report.status.in_([ReportStatus.NEW, ReportStatus.UNDER_REVIEW])
                )
            )
        )
        reports_count = result.scalar()

        # Уведомляем админов
        for admin_id in config.ADMIN_IDS:
            try:
                await callback.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🚨 <b>Новая жалоба!</b>

"
                        f"👤 <b>От:</b> {user.full_name} (ID: {user.telegram_id})
"
                        f"👤 <b>На:</b> ID {data['reported_id']}
"
                        f"📌 <b>Причина:</b> {data['reason_text']}
"
                        f"📝 <b>Описание:</b> {data['description']}

"
                        f"⚠️ Всего жалоб на пользователя: {reports_count}"
                    )
                )
            except Exception as e:
                print(f"Ошибка уведомления админа {admin_id}: {e}")

    await callback.message.edit_text(
        "✅ <b>Жалоба отправлена!</b>

"
        "Администратор рассмотрит её в ближайшее время.
"
        "Вы получите уведомление о результате."
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_report")
async def cancel_report(callback: CallbackQuery, state: FSMContext):
    """Отмена жалобы"""
    await callback.message.edit_text("❌ Жалоба отменена.")
    await state.clear()
    await callback.answer()


# === АДМИН: РАБОТА С ЖАЛОБАМИ ===

@router.message(F.text == "🛡️ Админ-панель")
async def admin_panel(message: Message, user: User = None):
    """Админ-панель"""
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return

    from bot.keyboards.main import admin_menu_keyboard
    await message.answer(
        "🛡️ <b>Админ-панель</b>

"
        "Выберите раздел:",
        reply_markup=admin_menu_keyboard()
    )


@router.message(F.text == "📋 Жалобы")
async def admin_reports(message: Message):
    """Список жалоб для админа"""
    if message.from_user.id not in config.ADMIN_IDS:
        return

    async with async_session() as session:
        result = await session.execute(
            select(Report, User).join(User, Report.reported_id == User.id).where(
                Report.status.in_([ReportStatus.NEW, ReportStatus.UNDER_REVIEW])
            ).order_by(Report.created_at)
        )
        reports = result.all()

    if not reports:
        await message.answer("📋 Новых жалоб нет.")
        return

    for report, reported_user in reports:
        from bot.keyboards.main import admin_report_keyboard
        text = (
            f"🚨 <b>Жалоба #{report.id}</b>

"
            f"👤 <b>На:</b> {reported_user.full_name}
"
            f"📱 <b>Телефон:</b> {reported_user.phone}
"
            f"📌 <b>Причина:</b> {report.reason}
"
            f"📝 <b>Описание:</b> {report.description}
"
            f"📅 <b>Дата:</b> {report.created_at.strftime('%d.%m.%Y %H:%M')}

"
            f"⚠️ <b>Статус:</b> {report.status.value}"
        )
        await message.answer(text, reply_markup=admin_report_keyboard(report.id, reported_user.id))


@router.callback_query(F.data.startswith("admin_block_"))
async def admin_block_user(callback: CallbackQuery, bot: Bot):
    """Админ: заблокировать пользователя"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    parts = callback.data.split("_")
    reported_id = int(parts[2])
    report_id = int(parts[3]) if len(parts) > 3 else None

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == reported_id)
        )
        user_to_block = result.scalar_one_or_none()

        if not user_to_block:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Блокируем пользователя
        user_to_block.status = UserStatus.BLOCKED
        user_to_block.blocked_at = datetime.utcnow()
        user_to_block.block_reason = f"Заблокирован админом ID {callback.from_user.id}"

        # Обновляем жалобу
        if report_id:
            result = await session.execute(
                select(Report).where(Report.id == report_id)
            )
            report = result.scalar_one_or_none()
            if report:
                report.status = ReportStatus.RESOLVED
                report.admin_decision = "block"
                report.resolved_by = callback.from_user.id
                report.resolved_at = datetime.utcnow()

        await session.commit()

        # Исключаем из общего чата
        try:
            await bot.ban_chat_member(
                chat_id=config.DISTRICT_CHAT_ID,
                user_id=user_to_block.telegram_id
            )
            # Разбаниваем, чтобы могли зайти, но бот будет блокировать
            await bot.unban_chat_member(
                chat_id=config.DISTRICT_CHAT_ID,
                user_id=user_to_block.telegram_id
            )
        except Exception as e:
            print(f"Ошибка исключения из чата: {e}")

        # Уведомляем заблокированного
        try:
            await bot.send_message(
                chat_id=user_to_block.telegram_id,
                text=(
                    "🚫 <b>Ваш аккаунт заблокирован</b>

"
                    "Причина: нарушение правил сообщества.
"
                    "Вы больше не можете пользоваться ботом и находиться в общем чате района.

"
                    "Если вы считаете, что это ошибка, обратитесь к администратору."
                )
            )
        except Exception as e:
            print(f"Ошибка уведомления заблокированного: {e}")

        # Уведомляем в канал
        try:
            await bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=(
                    f"🚫 <b>Пользователь заблокирован</b>

"
                    f"👤 {user_to_block.full_name}
"
                    f"📱 {user_to_block.phone}
"
                    f"📌 Причина: нарушение правил

"
                    f"Пользователь исключён из сообщества."
                )
            )
        except Exception as e:
            print(f"Ошибка публикации в канал: {e}")

    await callback.message.edit_text(
        f"✅ <b>Пользователь заблокирован!</b>

"
        f"👤 {user_to_block.full_name}
"
        f"🚫 Исключён из чата и заблокирован в боте."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_warn_"))
async def admin_warn_user(callback: CallbackQuery):
    """Админ: предупреждение пользователю"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    parts = callback.data.split("_")
    reported_id = int(parts[2])
    report_id = int(parts[3]) if len(parts) > 3 else None

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == reported_id)
        )
        user_to_warn = result.scalar_one_or_none()

        if not user_to_warn:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Обновляем жалобу
        if report_id:
            result = await session.execute(
                select(Report).where(Report.id == report_id)
            )
            report = result.scalar_one_or_none()
            if report:
                report.status = ReportStatus.RESOLVED
                report.admin_decision = "warn"
                report.resolved_by = callback.from_user.id
                report.resolved_at = datetime.utcnow()
                await session.commit()

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                chat_id=user_to_warn.telegram_id,
                text=(
                    "⚠️ <b>Предупреждение от администрации</b>

"
                    "На вас поступила жалоба от участника сообщества.
"
                    "Пожалуйста, соблюдайте правила взаимодействия.

"
                    "При повторном нарушении аккаунт будет заблокирован."
                )
            )
        except Exception as e:
            print(f"Ошибка отправки предупреждения: {e}")

    await callback.message.edit_text("⚠️ Предупреждение отправлено пользователю.")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_report(callback: CallbackQuery):
    """Админ: отклонить жалобу"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    report_id = int(callback.data.split("_")[2])

    async with async_session() as session:
        result = await session.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()

        if report:
            report.status = ReportStatus.REJECTED
            report.admin_decision = "reject"
            report.resolved_by = callback.from_user.id
            report.resolved_at = datetime.utcnow()
            await session.commit()

    await callback.message.edit_text("❌ Жалоба отклонена.")
    await callback.answer()
