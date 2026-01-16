import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        self._admin_ids = None

        # Зоны и столики
        self.ZONES = {
            "quiet": "Тихий зал",
            "karaoke": "Караоке зал"
        }

        self.TABLES = {
            "quiet": [1, 2, 3, 4, 5],
            "karaoke": [6, 7, 8, 9, 10]
        }

        # Время работы
        self.OPEN_TIME = 12
        self.CLOSE_TIME = 23

        # Для отладки
        print(f"BOT_TOKEN loaded: {'Yes' if self.BOT_TOKEN else 'No'}")

    @property
    def ADMIN_IDS(self):
        if self._admin_ids is None:
            admin_ids_str = os.getenv("ADMIN_IDS", "")
            print(f"Raw ADMIN_IDS from .env: '{admin_ids_str}'")

            if admin_ids_str and admin_ids_str.strip():
                try:
                    ids = []
                    for id_str in admin_ids_str.split(','):
                        id_str = id_str.strip()
                        if id_str:
                            ids.append(int(id_str))
                    self._admin_ids = ids
                    print(f"Parsed ADMIN_IDS: {self._admin_ids}")
                except ValueError as e:
                    print(f"Error parsing ADMIN_IDS: {e}")
                    self._admin_ids = []
            else:
                print("ADMIN_IDS is empty or not set")
                self._admin_ids = []
        return self._admin_ids


config = Config()