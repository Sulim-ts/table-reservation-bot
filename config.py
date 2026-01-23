import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        self._admin_ids = None

        # Зоны и столики (теперь один зал)
        self.ZONES = {
            "main": "🍽️ Основной зал"
        }

        self.TABLES = {
            "main": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # Все столики в основном зале
        }

        # Время работы
        self.OPEN_TIME = 12
        self.CLOSE_TIME = 23

        # Название ресторана
        self.RESTAURANT_NAME = "Вкусный уголок"

        # Контакты
        self.RESTAURANT_ADDRESS = "ул. Примерная, 123"
        self.RESTAURANT_PHONE = "+7 (999) 123-45-67"

        # Максимальное количество гостей за столом
        self.MAX_GUESTS = 10

        # Проверка загрузки токена
        if not self.BOT_TOKEN:
            print("⚠️ ВНИМАНИЕ: BOT_TOKEN не загружен!")
        else:
            print("✅ BOT_TOKEN успешно загружен")

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