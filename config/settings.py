import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN")
        self.database_paht = os.getenv("DATABASE_PATH")
        self.log_level = os.getenv("LOG_LEVEL")

        if not self.bot_token:
            raise ValueError("BOT_TOKEN is not set")
        if not self.database_path:
            raise ValueError("DATABASE_PATH is not set")
        if not self.log_level:
            raise ValueError("LOG_LEVEL is not set")

settings = Settings()