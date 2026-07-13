python
"""
Конфигурация бота "Парк Апрель"
Район: Парк Апрель
Координаты: 55.529598, 37.032715 (Яндекс Карты)
"""
import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Конфигурация бота"""

    # Токен бота
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # ID чатов
    DISTRICT_CHAT_ID: int = int(os.getenv("DISTRICT_CHAT_ID", "0"))
    CHANNEL_ID: int = int(os.getenv("CHANNEL_ID", "0"))

    # Администраторы
    ADMIN_IDS: List[int] = field(default_factory=list)

    # Название района
    DISTRICT_NAME: str = os.getenv("DISTRICT_NAME", "Парк Апрель")

    # Координаты центра района
    DISTRICT_LAT: float = float(os.getenv("DISTRICT_LAT", "55.529598"))
    DISTRICT_LON: float = float(os.getenv("DISTRICT_LON", "37.032715"))

    # Радиус района в км
    DISTRICT_RADIUS_KM: float = float(os.getenv("DISTRICT_RADIUS_KM", "2.0"))

    # База данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/park_april_bot.db")

    # Время жизни поездки после завершения (дней)
    RIDE_ARCHIVE_DAYS: int = int(os.getenv("RIDE_ARCHIVE_DAYS", "7"))

    # Минимальное количество жалоб для автоматического рассмотрения
    AUTO_REVIEW_REPORTS: int = int(os.getenv("AUTO_REVIEW_REPORTS", "3"))

    # Режим отладки
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # URL для вебхука (для Railway)
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

    def __post_init__(self):
        """Инициализация списка администраторов"""
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
        else:
            self.ADMIN_IDS = []


# Глобальный экземпляр конфигурации
config = BotConfig()