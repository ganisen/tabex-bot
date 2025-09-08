"""
Модуль подключения к SQLite базе данных.

Обеспечивает создание и управление соединениями с базой данных,
а также базовые операции с таблицами.
"""
import logging
import sqlite3
import aiosqlite
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Класс для управления соединениями с базой данных SQLite."""
    
    def __init__(self, db_path: str = "data/tabex_bot.db"):
        """
        Инициализация подключения к базе данных.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = Path(db_path)
        self.ensure_data_directory()
        logger.info(f"Инициализировано подключение к БД: {self.db_path}")
    
    def ensure_data_directory(self) -> None:
        """Создает директорию data, если она не существует."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Асинхронный контекст-менеджер для работы с базой данных.
        
        Yields:
            aiosqlite.Connection: Подключение к базе данных
        """
        conn = None
        try:
            conn = await aiosqlite.connect(str(self.db_path))
            # Включаем поддержку внешних ключей
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.commit()
            yield conn
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            if conn:
                await conn.rollback()
            raise
        finally:
            if conn:
                await conn.close()
    
    async def execute_query(self, query: str, params: tuple = ()) -> None:
        """
        Выполняет SQL-запрос без возврата данных.
        
        Args:
            query: SQL-запрос
            params: Параметры для запроса
        """
        async with self.get_connection() as conn:
            await conn.execute(query, params)
            await conn.commit()
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Выполняет SELECT-запрос и возвращает одну строку.
        
        Args:
            query: SQL-запрос
            params: Параметры для запроса
            
        Returns:
            Одна строка результата или None
        """
        async with self.get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, params)
            return await cursor.fetchone()
    
    async def fetch_all(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """
        Выполняет SELECT-запрос и возвращает все строки.
        
        Args:
            query: SQL-запрос
            params: Параметры для запроса
            
        Returns:
            Список всех строк результата
        """
        async with self.get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, params)
            return await cursor.fetchall()
    
    async def execute_script(self, script: str) -> None:
        """
        Выполняет SQL-скрипт (множественные команды).
        
        Args:
            script: SQL-скрипт для выполнения
        """
        async with self.get_connection() as conn:
            await conn.executescript(script)
            await conn.commit()
    
    async def table_exists(self, table_name: str) -> bool:
        """
        Проверяет существование таблицы в базе данных.
        
        Args:
            table_name: Имя таблицы для проверки
            
        Returns:
            True, если таблица существует
        """
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = await self.fetch_one(query, (table_name,))
        return result is not None
    
    async def get_table_info(self, table_name: str) -> list[sqlite3.Row]:
        """
        Получает информацию о структуре таблицы.
        
        Args:
            table_name: Имя таблицы
            
        Returns:
            Информация о колонках таблицы
        """
        query = f"PRAGMA table_info({table_name})"
        return await self.fetch_all(query)
    
    async def drop_table(self, table_name: str) -> None:
        """
        Удаляет таблицу из базы данных.
        
        Args:
            table_name: Имя таблицы для удаления
        """
        query = f"DROP TABLE IF EXISTS {table_name}"
        await self.execute_query(query)
        logger.info(f"Таблица {table_name} удалена")


# Глобальный экземпляр подключения к базе данных
_db_instance: Optional[DatabaseConnection] = None


def get_db() -> DatabaseConnection:
    """
    Возвращает глобальный экземпляр подключения к базе данных.
    
    Returns:
        DatabaseConnection: Экземпляр подключения к БД
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection()
    return _db_instance


async def init_database() -> None:
    """Инициализирует базу данных (создает таблицы, если нужно)."""
    from database.migrations import run_migrations
    
    logger.info("Инициализация базы данных...")
    db = get_db()
    
    try:
        await run_migrations()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise
