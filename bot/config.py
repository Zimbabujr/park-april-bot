"""
Конфигурация бота "Парк Апрель"
Район: Парк Апрель
Координаты: 55.529598, 37.032715 (Яндекс Карты)
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BotConfig:
    """Конфигурация бота"""

    # Токен бота (из переменных окружения)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

    # ID общего чата района (где все зарегистрированные пользователи)
    DISTRICT_CHAT_ID: int = int(os.getenv("DISTRICT_CHAT_ID", "-1001234567890"))

    # ID канала для публикации поездок
    CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "-1001234567891"))

    # ID администраторов (список через запятую)
    ADMIN_IDS: list[int] = None

    # Название района
    DISTRICT_NAME: str = "Парк Апрель"

    # Координаты центра района (из Яндекс Карт)
    DISTRICT_LAT: float = 55.529598
    DISTRICT_LON: float = 37.032715

    # Радиус района в км (в пределах которого работает бот)
    DISTRICT_RADIUS_KM: float = 2.0

    # База данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///park_april_bot.db")

    # Время жизни поездки после завершения (дней)
    RIDE_ARCHIVE_DAYS: int = 7

    # Минимальное количество жалоб для автоматического рассмотрения
    AUTO_REVIEW_REPORTS: int = 3

    def __post_init__(self):
        if self.ADMIN_IDS is None:
            admin_ids_str = os.getenv("ADMIN_IDS", "")
            if admin_ids_str:
                object.__setattr__(self, 'ADMIN_IDS', [int(x.strip()) for x in admin_ids_str.split(",")])
            else:
                object.__setattr__(self, 'ADMIN_IDS', [])


# Глобальный экземпляр конфигурации
config = BotConfig()
