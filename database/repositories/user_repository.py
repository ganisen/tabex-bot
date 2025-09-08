"""
Репозиторий для работы с пользователями.

Обеспечивает CRUD операции для модели User с поддержкой
гендерной дифференциации и поиска по различным критериям.
"""
import logging
from typing import Optional, List
from datetime import datetime

from core.models.user import User
from database.connection import get_db

logger = logging.getLogger(__name__)


class UserRepository:
    """Репозиторий для работы с пользователями в базе данных."""
    
    def __init__(self):
        self.db = get_db()
    
    async def create(self, user: User) -> User:
        """
        Создает нового пользователя в базе данных.
        
        Args:
            user: Объект пользователя для создания
            
        Returns:
            User: Созданный пользователь с присвоенным ID
            
        Raises:
            ValueError: Если пользователь с таким telegram_id уже существует
        """
        # Проверяем, что пользователь не существует
        existing = await self.get_by_telegram_id(user.telegram_id)
        if existing:
            raise ValueError(f"Пользователь с telegram_id {user.telegram_id} уже существует")
        
        query = """
            INSERT INTO users (telegram_id, first_name, username, gender, timezone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            user.telegram_id,
            user.first_name,
            user.username,
            user.gender,
            user.timezone,
            user.created_at or datetime.now(),
            user.updated_at or datetime.now()
        )
        
        try:
            # Выполняем вставку
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, params)
                user_id = cursor.lastrowid
                await conn.commit()
            
            # Устанавливаем ID и возвращаем пользователя
            user.user_id = user_id
            logger.info(f"Создан пользователь: {user}")
            return user
            
        except Exception as e:
            logger.error(f"Ошибка создания пользователя: {e}")
            raise
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Получает пользователя по внутреннему ID.
        
        Args:
            user_id: Внутренний ID пользователя
            
        Returns:
            User или None, если пользователь не найден
        """
        query = "SELECT * FROM users WHERE user_id = ?"
        
        try:
            row = await self.db.fetch_one(query, (user_id,))
            return self._row_to_user(row) if row else None
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователя по ID {user_id}: {e}")
            raise
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получает пользователя по Telegram ID.
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            User или None, если пользователь не найден
        """
        query = "SELECT * FROM users WHERE telegram_id = ?"
        
        try:
            row = await self.db.fetch_one(query, (telegram_id,))
            return self._row_to_user(row) if row else None
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователя по telegram_id {telegram_id}: {e}")
            raise
    
    async def update(self, user: User) -> User:
        """
        Обновляет данные пользователя.
        
        Args:
            user: Объект пользователя с обновленными данными
            
        Returns:
            User: Обновленный пользователь
            
        Raises:
            ValueError: Если пользователь не найден
        """
        if not user.user_id:
            raise ValueError("Для обновления пользователя необходимо указать user_id")
        
        # Проверяем существование пользователя
        existing = await self.get_by_id(user.user_id)
        if not existing:
            raise ValueError(f"Пользователь с ID {user.user_id} не найден")
        
        query = """
            UPDATE users 
            SET first_name = ?, username = ?, gender = ?, timezone = ?, updated_at = ?
            WHERE user_id = ?
        """
        
        params = (
            user.first_name,
            user.username,
            user.gender,
            user.timezone,
            datetime.now(),
            user.user_id
        )
        
        try:
            await self.db.execute_query(query, params)
            user.updated_at = datetime.now()
            logger.info(f"Обновлен пользователь: {user}")
            return user
            
        except Exception as e:
            logger.error(f"Ошибка обновления пользователя {user.user_id}: {e}")
            raise
    
    async def delete(self, user_id: int) -> bool:
        """
        Удаляет пользователя из базы данных.
        
        Args:
            user_id: ID пользователя для удаления
            
        Returns:
            bool: True, если пользователь был удален
        """
        query = "DELETE FROM users WHERE user_id = ?"
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, (user_id,))
                rows_affected = cursor.rowcount
                await conn.commit()
            
            success = rows_affected > 0
            if success:
                logger.info(f"Удален пользователь с ID {user_id}")
            else:
                logger.warning(f"Пользователь с ID {user_id} не найден для удаления")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя {user_id}: {e}")
            raise
    
    async def get_all(self) -> List[User]:
        """
        Получает список всех пользователей.
        
        Returns:
            List[User]: Список всех пользователей
        """
        query = "SELECT * FROM users ORDER BY created_at DESC"
        
        try:
            rows = await self.db.fetch_all(query)
            return [self._row_to_user(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения всех пользователей: {e}")
            raise
    
    async def get_by_gender(self, gender: str) -> List[User]:
        """
        Получает пользователей по гендеру.
        
        Args:
            gender: Гендер для фильтрации ('male' или 'female')
            
        Returns:
            List[User]: Список пользователей указанного гендера
        """
        if gender not in ['male', 'female']:
            raise ValueError("Гендер должен быть 'male' или 'female'")
        
        query = "SELECT * FROM users WHERE gender = ? ORDER BY created_at DESC"
        
        try:
            rows = await self.db.fetch_all(query, (gender,))
            return [self._row_to_user(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователей по гендеру {gender}: {e}")
            raise
    
    async def search_by_name(self, name_pattern: str) -> List[User]:
        """
        Поиск пользователей по имени (частичное совпадение).
        
        Args:
            name_pattern: Паттерн для поиска в имени
            
        Returns:
            List[User]: Список найденных пользователей
        """
        query = """
            SELECT * FROM users 
            WHERE first_name LIKE ? OR username LIKE ?
            ORDER BY created_at DESC
        """
        
        pattern = f"%{name_pattern}%"
        
        try:
            rows = await self.db.fetch_all(query, (pattern, pattern))
            return [self._row_to_user(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка поиска пользователей по имени '{name_pattern}': {e}")
            raise
    
    async def get_user_count(self) -> int:
        """
        Получает общее количество пользователей.
        
        Returns:
            int: Количество пользователей в системе
        """
        query = "SELECT COUNT(*) as count FROM users"
        
        try:
            result = await self.db.fetch_one(query)
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Ошибка получения количества пользователей: {e}")
            raise
    
    async def get_gender_statistics(self) -> dict:
        """
        Получает статистику по гендерному распределению.
        
        Returns:
            dict: Статистика по гендерам {'male': count, 'female': count}
        """
        query = """
            SELECT gender, COUNT(*) as count 
            FROM users 
            GROUP BY gender
        """
        
        try:
            rows = await self.db.fetch_all(query)
            stats = {'male': 0, 'female': 0}
            
            for row in rows:
                stats[row['gender']] = row['count']
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики по гендерам: {e}")
            raise
    
    def _row_to_user(self, row) -> User:
        """
        Преобразует строку из базы данных в объект User.
        
        Args:
            row: Строка из базы данных
            
        Returns:
            User: Объект пользователя
        """
        return User(
            user_id=row['user_id'],
            telegram_id=row['telegram_id'],
            first_name=row['first_name'],
            username=row['username'],
            gender=row['gender'],
            timezone=row['timezone'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
