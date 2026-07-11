"""
Главный файл бота "Парк Апрель"
Район: Парк Апрель
Координаты: 55.529598, 37.032715
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import config
from bot.models.database import init_db
from bot.middlewares.auth import AuthMiddleware, BlockCheckMiddleware
from bot.handlers import registration_router, rides_router, reports_router
from bot.services.notifications import notify_upcoming_rides, archive_old_rides

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция"""
    logger.info(f"🚀 Запуск бота района «{config.DISTRICT_NAME}»")

    # Инициализация БД
    await init_db()
    logger.info("✅ База данных инициализирована")

    # Создание бота
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот @{bot_info.username} запущен")

    # Создание диспетчера
    dp = Dispatcher()

    # Регистрация middleware
    dp.update.outer_middleware(AuthMiddleware())
    dp.update.outer_middleware(BlockCheckMiddleware())
    logger.info("✅ Middleware зарегистрированы")

    # Регистрация роутеров
    dp.include_router(registration_router)
    dp.include_router(rides_router)
    dp.include_router(reports_router)
    logger.info("✅ Роутеры зарегистрированы")

    # Настройка планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        notify_upcoming_rides,
        "cron",
        hour="*",
        minute=0,
        args=[bot]
    )
    scheduler.add_job(
        archive_old_rides,
        "cron",
        hour=3,
        minute=0
    )
    scheduler.start()
    logger.info("✅ Планировщик запущен")

    # Удаление вебхука и запуск polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🔄 Начало polling...")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("🛑 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
