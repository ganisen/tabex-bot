"""
Репозиторий для работы с курсами лечения Табекс.

Обеспечивает CRUD операции для модели TreatmentCourse,
управление фазами лечения и переходами между персонажами.
"""
import logging
from typing import Optional, List
from datetime import datetime, date

from core.models.treatment import TreatmentCourse, TreatmentStatus
from database.connection import get_db

logger = logging.getLogger(__name__)


class TreatmentRepository:
    """Репозиторий для работы с курсами лечения в базе данных."""
    
    def __init__(self):
        self.db = get_db()
    
    async def create(self, treatment: TreatmentCourse) -> TreatmentCourse:
        """
        Создает новый курс лечения в базе данных.
        
        Args:
            treatment: Объект курса лечения для создания
            
        Returns:
            TreatmentCourse: Созданный курс с присвоенным ID
        """
        query = """
            INSERT INTO treatment_courses (
                user_id, start_date, current_phase, current_character, 
                status, smoking_quit_date, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            treatment.user_id,
            treatment.start_date.isoformat(),
            treatment.current_phase,
            treatment.current_character,
            treatment.status,
            treatment.smoking_quit_date.isoformat() if treatment.smoking_quit_date else None,
            treatment.created_at or datetime.now(),
            treatment.updated_at or datetime.now()
        )
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, params)
                course_id = cursor.lastrowid
                await conn.commit()
            
            treatment.course_id = course_id
            logger.info(f"Создан курс лечения: {treatment}")
            return treatment
            
        except Exception as e:
            logger.error(f"Ошибка создания курса лечения: {e}")
            raise
    
    async def get_by_id(self, course_id: int) -> Optional[TreatmentCourse]:
        """
        Получает курс лечения по ID.
        
        Args:
            course_id: ID курса лечения
            
        Returns:
            TreatmentCourse или None, если курс не найден
        """
        query = "SELECT * FROM treatment_courses WHERE course_id = ?"
        
        try:
            row = await self.db.fetch_one(query, (course_id,))
            return self._row_to_treatment(row) if row else None
            
        except Exception as e:
            logger.error(f"Ошибка получения курса по ID {course_id}: {e}")
            raise
    
    async def get_active_by_user_id(self, user_id: int) -> Optional[TreatmentCourse]:
        """
        Получает активный курс лечения пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            TreatmentCourse или None, если активный курс не найден
        """
        query = """
            SELECT * FROM treatment_courses 
            WHERE user_id = ? AND status = 'active' 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        
        try:
            row = await self.db.fetch_one(query, (user_id,))
            return self._row_to_treatment(row) if row else None
            
        except Exception as e:
            logger.error(f"Ошибка получения активного курса для пользователя {user_id}: {e}")
            raise
    
    async def get_all_by_user_id(self, user_id: int) -> List[TreatmentCourse]:
        """
        Получает все курсы лечения пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[TreatmentCourse]: Список курсов пользователя
        """
        query = """
            SELECT * FROM treatment_courses 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """
        
        try:
            rows = await self.db.fetch_all(query, (user_id,))
            return [self._row_to_treatment(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения курсов для пользователя {user_id}: {e}")
            raise
    
    async def update(self, treatment: TreatmentCourse) -> TreatmentCourse:
        """
        Обновляет курс лечения.
        
        Args:
            treatment: Объект курса с обновленными данными
            
        Returns:
            TreatmentCourse: Обновленный курс
        """
        if not treatment.course_id:
            raise ValueError("Для обновления курса необходимо указать course_id")
        
        query = """
            UPDATE treatment_courses 
            SET current_phase = ?, current_character = ?, status = ?, 
                smoking_quit_date = ?, updated_at = ?
            WHERE course_id = ?
        """
        
        params = (
            treatment.current_phase,
            treatment.current_character,
            treatment.status,
            treatment.smoking_quit_date.isoformat() if treatment.smoking_quit_date else None,
            datetime.now(),
            treatment.course_id
        )
        
        try:
            await self.db.execute_query(query, params)
            treatment.updated_at = datetime.now()
            logger.info(f"Обновлен курс лечения: {treatment}")
            return treatment
            
        except Exception as e:
            logger.error(f"Ошибка обновления курса {treatment.course_id}: {e}")
            raise
    
    async def update_phase_and_character(self, course_id: int, phase: int, character: str) -> bool:
        """
        Обновляет фазу и персонажа курса лечения.
        
        Args:
            course_id: ID курса лечения
            phase: Новая фаза (1-5)
            character: Новый персонаж
            
        Returns:
            bool: True, если обновление прошло успешно
        """
        query = """
            UPDATE treatment_courses 
            SET current_phase = ?, current_character = ?, updated_at = ?
            WHERE course_id = ?
        """
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, (phase, character, datetime.now(), course_id))
                rows_affected = cursor.rowcount
                await conn.commit()
            
            success = rows_affected > 0
            if success:
                logger.info(f"Обновлена фаза {phase} и персонаж {character} для курса {course_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка обновления фазы и персонажа для курса {course_id}: {e}")
            raise
    
    async def mark_smoking_quit_date(self, course_id: int, quit_date: date) -> bool:
        """
        Отмечает дату полного отказа от курения.
        
        Args:
            course_id: ID курса лечения
            quit_date: Дата отказа от курения
            
        Returns:
            bool: True, если обновление прошло успешно
        """
        query = """
            UPDATE treatment_courses 
            SET smoking_quit_date = ?, updated_at = ?
            WHERE course_id = ?
        """
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, (quit_date.isoformat(), datetime.now(), course_id))
                rows_affected = cursor.rowcount
                await conn.commit()
            
            success = rows_affected > 0
            if success:
                logger.info(f"Установлена дата отказа от курения {quit_date} для курса {course_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка установки даты отказа от курения для курса {course_id}: {e}")
            raise
    
    async def complete_course(self, course_id: int) -> bool:
        """
        Помечает курс как завершенный.
        
        Args:
            course_id: ID курса лечения
            
        Returns:
            bool: True, если курс был успешно завершен
        """
        return await self._update_status(course_id, TreatmentStatus.COMPLETED.value)
    
    async def fail_course(self, course_id: int) -> bool:
        """
        Помечает курс как проваленный.
        
        Args:
            course_id: ID курса лечения
            
        Returns:
            bool: True, если курс был помечен как проваленный
        """
        return await self._update_status(course_id, TreatmentStatus.FAILED.value)
    
    async def pause_course(self, course_id: int) -> bool:
        """
        Приостанавливает курс лечения.
        
        Args:
            course_id: ID курса лечения
            
        Returns:
            bool: True, если курс был приостановлен
        """
        return await self._update_status(course_id, TreatmentStatus.PAUSED.value)
    
    async def resume_course(self, course_id: int) -> bool:
        """
        Возобновляет приостановленный курс лечения.
        
        Args:
            course_id: ID курса лечения
            
        Returns:
            bool: True, если курс был возобновлен
        """
        return await self._update_status(course_id, TreatmentStatus.ACTIVE.value)
    
    async def get_courses_by_status(self, status: str) -> List[TreatmentCourse]:
        """
        Получает курсы по статусу.
        
        Args:
            status: Статус курсов для получения
            
        Returns:
            List[TreatmentCourse]: Список курсов с указанным статусом
        """
        query = """
            SELECT * FROM treatment_courses 
            WHERE status = ? 
            ORDER BY created_at DESC
        """
        
        try:
            rows = await self.db.fetch_all(query, (status,))
            return [self._row_to_treatment(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения курсов по статусу {status}: {e}")
            raise
    
    async def get_courses_by_character(self, character: str) -> List[TreatmentCourse]:
        """
        Получает активные курсы с определенным персонажем.
        
        Args:
            character: Имя персонажа
            
        Returns:
            List[TreatmentCourse]: Список курсов с указанным персонажем
        """
        query = """
            SELECT * FROM treatment_courses 
            WHERE current_character = ? AND status = 'active'
            ORDER BY created_at DESC
        """
        
        try:
            rows = await self.db.fetch_all(query, (character,))
            return [self._row_to_treatment(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка получения курсов для персонажа {character}: {e}")
            raise
    
    async def _update_status(self, course_id: int, status: str) -> bool:
        """
        Обновляет статус курса лечения.
        
        Args:
            course_id: ID курса
            status: Новый статус
            
        Returns:
            bool: True, если обновление прошло успешно
        """
        query = """
            UPDATE treatment_courses 
            SET status = ?, updated_at = ?
            WHERE course_id = ?
        """
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, (status, datetime.now(), course_id))
                rows_affected = cursor.rowcount
                await conn.commit()
            
            success = rows_affected > 0
            if success:
                logger.info(f"Статус курса {course_id} изменен на {status}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка изменения статуса курса {course_id} на {status}: {e}")
            raise
    
    async def delete_all_by_user_id(self, user_id: int) -> bool:
        """
        Удаляет все курсы лечения пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True, если курсы были удалены
        """
        query = "DELETE FROM treatment_courses WHERE user_id = ?"
        
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, (user_id,))
                rows_affected = cursor.rowcount
                await conn.commit()
            
            logger.info(f"Удалено {rows_affected} курсов лечения для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления курсов лечения для пользователя {user_id}: {e}")
            raise

    def _row_to_treatment(self, row) -> TreatmentCourse:
        """
        Преобразует строку из базы данных в объект TreatmentCourse.
        
        Args:
            row: Строка из базы данных
            
        Returns:
            TreatmentCourse: Объект курса лечения
        """
        return TreatmentCourse(
            course_id=row['course_id'],
            user_id=row['user_id'],
            start_date=date.fromisoformat(row['start_date']),
            current_phase=row['current_phase'],
            current_character=row['current_character'],
            status=row['status'],
            smoking_quit_date=date.fromisoformat(row['smoking_quit_date']) if row['smoking_quit_date'] else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
