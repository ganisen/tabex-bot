import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN")
        self.database_path = os.getenv("DATABASE_PATH")
        self.log_level = os.getenv("LOG_LEVEL")

        if not self.bot_token:
            raise ValueError("BOT_TOKEN не установлен в переменных окружения")
        if not self.database_path:
            raise ValueError("DATABASE_PATH не установлен")
        if not self.log_level:
            raise ValueError("LOG_LEVEL не установлен")

settings = Settings()