import os
from dotenv import load_dotenv
from restaurant_config import RESTAURANT_CONFIG, get_working_hours, get_last_booking_time

load_dotenv()


class Config:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        self._admin_ids = None

        # Загружаем конфигурацию из restaurant_config.py
        self.restaurant_config = RESTAURANT_CONFIG

        # Время работы (разбираем на часы и минуты)
        self.OPEN_TIME_STR = self.restaurant_config["open_time"]
        self.CLOSE_TIME_STR = self.restaurant_config["close_time"]

        # Разбираем время на часы и минуты
        self.OPEN_HOUR, self.OPEN_MINUTE = map(int, self.OPEN_TIME_STR.split(':'))
        self.CLOSE_HOUR, self.CLOSE_MINUTE = map(int, self.CLOSE_TIME_STR.split(':'))

        # Преобразуем в минуты для удобства расчетов
        self.OPEN_TIME_MINUTES = self.OPEN_HOUR * 60 + self.OPEN_MINUTE
        self.CLOSE_TIME_MINUTES = self.CLOSE_HOUR * 60 + self.CLOSE_MINUTE

        # Получаем время последней брони (за час до закрытия)
        self.LAST_BOOKING_TIME_STR = get_last_booking_time()
        last_booking_hour, last_booking_minute = map(int, self.LAST_BOOKING_TIME_STR.split(':'))
        self.LAST_BOOKING_TIME_MINUTES = last_booking_hour * 60 + last_booking_minute

        # Интервал времени для бронирования
        self.TIME_INTERVAL = self.restaurant_config["time_interval"]  # в минутах

        # Название ресторана
        self.RESTAURANT_NAME = self.restaurant_config["name"]

        # Контакты
        self.RESTAURANT_ADDRESS = self.restaurant_config["address"]
        self.RESTAURANT_PHONE = self.restaurant_config["phone"]

        # Максимальное количество гостей за столом
        self.MAX_GUESTS = self.restaurant_config["max_guests"]

        # Зоны и столики
        self.ZONES = self.restaurant_config["zones"]
        self.TABLES = {
            "main": self.restaurant_config["tables"]  # Все столики в основном зале
        }

        # Проверка загрузки токена
        if not self.BOT_TOKEN:
            print("⚠️ ВНИМАНИЕ: BOT_TOKEN не загружен!")
        else:
            print("✅ BOT_TOKEN успешно загружен")

    @property
    def WORKING_HOURS_STR(self):
        """Время работы в строковом формате"""
        return f"{self.OPEN_TIME_STR} - {self.CLOSE_TIME_STR}"

    @property
    def LAST_BOOKING_HOUR(self):
        """Час последней брони"""
        return int(self.LAST_BOOKING_TIME_STR.split(':')[0])

    @property
    def LAST_BOOKING_MINUTE(self):
        """Минута последней брони"""
        return int(self.LAST_BOOKING_TIME_STR.split(':')[1])

    @property
    def ADMIN_IDS(self):
        if self._admin_ids is None:
            admin_ids_str = os.getenv("ADMIN_IDS", "")
            print(f"⚙️ Загрузка ADMIN_IDS из .env: '{admin_ids_str}'")

            if admin_ids_str and admin_ids_str.strip():
                try:
                    ids = []
                    for id_str in admin_ids_str.split(','):
                        id_str = id_str.strip()
                        if id_str:
                            ids.append(int(id_str))
                    self._admin_ids = ids
                    print(f"✅ Администраторы загружены: {self._admin_ids}")
                except ValueError as e:
                    print(f"❌ Ошибка парсинга ADMIN_IDS: {e}")
                    self._admin_ids = []
            else:
                print("ℹ️ ADMIN_IDS не указаны или пустые")
                self._admin_ids = []
        return self._admin_ids


config = Config()

