"""
Репозиторий для работы с записями о приёме таблеток и взаимодействиями с персонажами.

Обеспечивает CRUD операции для моделей TabexLog и CharacterInteraction,
управление расписанием приёмов и историей взаимодействий.
"""
import logging
from typing import Optional, List
from datetime import datetime, date, timedelta

from core.models.tabex_log import TabexLog, TabexLogStatus, CharacterInteraction
from database.connection import get_db

logger = logging.getLogger(__name__)


class TabexRepository:
    """Репозиторий для работы с записями приёма Табекс в базе данных."""
    
    def __init__(self):
        self.db = get_db()
    
    # === ОПЕРАЦИИ С ЗАПИСЯМИ ПРИЁМА ТАБЛЕТОК ===
    
    async def create_log(self, log: TabexLog) -> TabexLog:
        """
        Создает новую запись о приёме таблетки.
        
        Args:
            log: Объект записи для создания
            
        Returns:
            TabexLog: Созданная запись с присвоенным ID
        """
        query = """
            INSERT INTO tabex_logs (
                course_id, scheduled_time, actual_time, status, 
                phase, character_response, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            log.course_id,
            log.scheduled_time.isoformat(),
            log.actual_time.isoformat() if log.actual_time else None,
            log.status,
            log.phase,
            log.character_response,
            log.created_at or datetime.now()
        )
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, params)
                log_id = cursor.lastrowid
                await conn.commit()
            
            log.log_id = log_id
            logger.info(f"Создана запись о приёме: {log}")
            return log
            
        except Exception as e:
            logger.error(f"Ошибка создания записи приёма: {e}")
            raise
    
    async def get_log_by_id(self, log_id: int) -> Optional[TabexLog]:
        """
        Получает запись о приёме по ID.
        
        Args:
            log_id: ID записи
            
        Returns:
            TabexLog или None, если запись не найдена
        """
        query = "SELECT * FROM tabex_logs WHERE log_id = ?"
        
        try:
            row = await self.db.fetch_one(query, (log_id,))
            return self._row_to_log(row) if row else None
            
        except Exception as e:
            logger.error(f"Ошибка получения записи по ID {log_id}: {e}")
            raise
    
    async def get_logs_by_course_id(self, course_id: int) -> List[TabexLog]:
        """
        Получает все записи приёма для курса лечения.
        
        Args:
            course_id: ID курса лечения
            
        Returns:
            List[TabexLog]: Список записей приёма
        """
        query = """
            SELECT * FROM tabex_logs 
            WHERE course_id = ? 
            ORDER BY scheduled_time DESC
        """
        
        try:
            rows = await self.db.fetch_all(query, (course_id,))
            return [self._row_to_log(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения записей для курса {course_id}: {e}")
            raise
    
    async def get_scheduled_logs(self, course_id: int) -> List[TabexLog]:
        """
        Получает запланированные приёмы для курса.
        
        Args:
            course_id: ID курса лечения
            
        Returns:
            List[TabexLog]: Список запланированных приёмов
        """
        query = """
            SELECT * FROM tabex_logs 
            WHERE course_id = ? AND status = 'scheduled'
            ORDER BY scheduled_time ASC
        """
        
        try:
            rows = await self.db.fetch_all(query, (course_id,))
            return [self._row_to_log(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения запланированных записей для курса {course_id}: {e}")
            raise
    
    async def get_overdue_logs(self, course_id: int, cutoff_time: datetime) -> List[TabexLog]:
        """
        Получает просроченные приёмы для курса.
        
        Args:
            course_id: ID курса лечения
            cutoff_time: Время, после которого приём считается просроченным
            
        Returns:
            List[TabexLog]: Список просроченных приёмов
        """
        query = """
            SELECT * FROM tabex_logs 
            WHERE course_id = ? AND status = 'scheduled' AND scheduled_time < ?
            ORDER BY scheduled_time ASC
        """
        
        try:
            rows = await self.db.fetch_all(query, (course_id, cutoff_time.isoformat()))
            return [self._row_to_log(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения просроченных записей для курса {course_id}: {e}")
            raise
    
    async def update_log(self, log: TabexLog) -> TabexLog:
        """
        Обновляет запись о приёме таблетки.
        
        Args:
            log: Объект записи с обновленными данными
            
        Returns:
            TabexLog: Обновленная запись
        """
        if not log.log_id:
            raise ValueError("Для обновления записи необходимо указать log_id")
        
        query = """
            UPDATE tabex_logs 
            SET actual_time = ?, status = ?, character_response = ?
            WHERE log_id = ?
        """
        
        params = (
            log.actual_time.isoformat() if log.actual_time else None,
            log.status,
            log.character_response,
            log.log_id
        )
        
        try:
            await self.db.execute_query(query, params)
            logger.info(f"Обновлена запись приёма: {log}")
            return log
            
        except Exception as e:
            logger.error(f"Ошибка обновления записи {log.log_id}: {e}")
            raise
    
    async def mark_log_taken(self, log_id: int, actual_time: datetime, character_response: str = "") -> bool:
        """
        Отмечает приём как выполненный.
        
        Args:
            log_id: ID записи
            actual_time: Время фактического приёма
            character_response: Реакция персонажа
            
        Returns:
            bool: True, если запись была обновлена
        """
        query = """
            UPDATE tabex_logs 
            SET status = 'taken', actual_time = ?, character_response = ?
            WHERE log_id = ?
        """
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, (actual_time.isoformat(), character_response, log_id))
                rows_affected = cursor.rowcount
                await conn.commit()
            
            success = rows_affected > 0
            if success:
                logger.info(f"Приём {log_id} отмечен как принятый в {actual_time}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка отметки приёма {log_id} как принятого: {e}")
            raise
    
    async def mark_log_missed(self, log_id: int, character_response: str = "") -> bool:
        """
        Отмечает приём как пропущенный.
        
        Args:
            log_id: ID записи
            character_response: Реакция персонажа на пропуск
            
        Returns:
            bool: True, если запись была обновлена
        """
        query = """
            UPDATE tabex_logs 
            SET status = 'missed', character_response = ?
            WHERE log_id = ?
        """
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, (character_response, log_id))
                rows_affected = cursor.rowcount
                await conn.commit()
            
            success = rows_affected > 0
            if success:
                logger.info(f"Приём {log_id} отмечен как пропущенный")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка отметки приёма {log_id} как пропущенного: {e}")
            raise
    
    async def get_course_statistics(self, course_id: int) -> dict:
        """
        Получает статистику по курсу лечения.
        
        Args:
            course_id: ID курса лечения
            
        Returns:
            dict: Статистика приёмов (taken, missed, scheduled, total)
        """
        query = """
            SELECT status, COUNT(*) as count
            FROM tabex_logs
            WHERE course_id = ?
            GROUP BY status
        """
        
        try:
            rows = await self.db.fetch_all(query, (course_id,))
            
            stats = {'taken': 0, 'missed': 0, 'scheduled': 0, 'skipped': 0, 'total': 0}
            
            for row in rows:
                stats[row['status']] = row['count']
                stats['total'] += row['count']
            
            # Вычисляем процент соблюдения режима
            if stats['total'] > 0:
                completed = stats['taken'] + stats['missed'] + stats['skipped']
                stats['compliance_rate'] = round((stats['taken'] / completed * 100), 1) if completed > 0 else 0.0
            else:
                stats['compliance_rate'] = 0.0
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики для курса {course_id}: {e}")
            raise
    
    # === ОПЕРАЦИИ С ВЗАИМОДЕЙСТВИЯМИ ПЕРСОНАЖЕЙ ===
    
    async def create_interaction(self, interaction: CharacterInteraction) -> CharacterInteraction:
        """
        Создает новое взаимодействие с персонажем.
        
        Args:
            interaction: Объект взаимодействия для создания
            
        Returns:
            CharacterInteraction: Созданное взаимодействие с присвоенным ID
        """
        query = """
            INSERT INTO character_interactions (
                course_id, character_name, interaction_type, 
                message_text, user_response, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        params = (
            interaction.course_id,
            interaction.character_name,
            interaction.interaction_type,
            interaction.message_text,
            interaction.user_response,
            interaction.created_at or datetime.now()
        )
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, params)
                interaction_id = cursor.lastrowid
                await conn.commit()
            
            interaction.interaction_id = interaction_id
            logger.info(f"Создано взаимодействие: {interaction}")
            return interaction
            
        except Exception as e:
            logger.error(f"Ошибка создания взаимодействия: {e}")
            raise
    
    async def get_interactions_by_course_id(self, course_id: int) -> List[CharacterInteraction]:
        """
        Получает все взаимодействия для курса лечения.
        
        Args:
            course_id: ID курса лечения
            
        Returns:
            List[CharacterInteraction]: Список взаимодействий
        """
        query = """
            SELECT * FROM character_interactions 
            WHERE course_id = ? 
            ORDER BY created_at DESC
        """
        
        try:
            rows = await self.db.fetch_all(query, (course_id,))
            return [self._row_to_interaction(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения взаимодействий для курса {course_id}: {e}")
            raise
    
    async def get_interactions_by_character(self, course_id: int, character_name: str) -> List[CharacterInteraction]:
        """
        Получает взаимодействия с определенным персонажем.
        
        Args:
            course_id: ID курса лечения
            character_name: Имя персонажа
            
        Returns:
            List[CharacterInteraction]: Список взаимодействий с персонажем
        """
        query = """
            SELECT * FROM character_interactions 
            WHERE course_id = ? AND character_name = ?
            ORDER BY created_at DESC
        """
        
        try:
            rows = await self.db.fetch_all(query, (course_id, character_name))
            return [self._row_to_interaction(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения взаимодействий с {character_name} для курса {course_id}: {e}")
            raise
    
    def _row_to_log(self, row) -> TabexLog:
        """
        Преобразует строку из базы данных в объект TabexLog.
        
        Args:
            row: Строка из базы данных
            
        Returns:
            TabexLog: Объект записи приёма
        """
        return TabexLog(
            log_id=row['log_id'],
            course_id=row['course_id'],
            scheduled_time=datetime.fromisoformat(row['scheduled_time']),
            actual_time=datetime.fromisoformat(row['actual_time']) if row['actual_time'] else None,
            status=row['status'],
            phase=row['phase'],
            character_response=row['character_response'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )
    
    async def delete_all_logs_for_user(self, user_id: int) -> bool:
        """
        Удаляет все записи приёма таблеток для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True, если записи были удалены
        """
        query = """
            DELETE FROM tabex_logs 
            WHERE course_id IN (
                SELECT course_id FROM treatment_courses WHERE user_id = ?
            )
        """
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, (user_id,))
                rows_affected = cursor.rowcount
                await conn.commit()
            
            logger.info(f"Удалено {rows_affected} записей приёма для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления записей приёма для пользователя {user_id}: {e}")
            raise
    
    async def delete_all_interactions_for_user(self, user_id: int) -> bool:
        """
        Удаляет все взаимодействия с персонажами для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True, если взаимодействия были удалены
        """
        query = """
            DELETE FROM character_interactions 
            WHERE course_id IN (
                SELECT course_id FROM treatment_courses WHERE user_id = ?
            )
        """
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, (user_id,))
                rows_affected = cursor.rowcount
                await conn.commit()
            
            logger.info(f"Удалено {rows_affected} взаимодействий с персонажами для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления взаимодействий для пользователя {user_id}: {e}")
            raise

    def _row_to_interaction(self, row) -> CharacterInteraction:
        """
        Преобразует строку из базы данных в объект CharacterInteraction.
        
        Args:
            row: Строка из базы данных
            
        Returns:
            CharacterInteraction: Объект взаимодействия
        """
        return CharacterInteraction(
            interaction_id=row['interaction_id'],
            course_id=row['course_id'],
            character_name=row['character_name'],
            interaction_type=row['interaction_type'],
            message_text=row['message_text'],
            user_response=row['user_response'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )
