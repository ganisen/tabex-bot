"""
Модель курса лечения Табекс с фазами и персонажами.

Отслеживает прогресс пользователя через различные фазы лечения
и смену персонажей Плоского мира.
"""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from enum import Enum


class TreatmentStatus(Enum):
    """Статусы курса лечения."""
    ACTIVE = "active"
    COMPLETED = "completed" 
    FAILED = "failed"
    PAUSED = "paused"


class TreatmentPhase(Enum):
    """Фазы лечения Табекс."""
    PHASE_1 = 1  # Дни 1-3: Гаспод, каждые 2 часа, 6 таблеток/день
    PHASE_2 = 2  # Дни 4-12: Шнобби & Колон, каждые 2.5 часа, 5 таблеток/день
    PHASE_3 = 3  # Дни 13-16: Ангва, каждые 3 часа, 4 таблетки/день
    PHASE_4 = 4  # Дни 17-20: Моркоу, каждые 5 часов, 3 таблетки/день
    PHASE_5 = 5  # Дни 21-25: Ваймс, 1-2 таблетки/день


@dataclass 
class TreatmentCourse:
    """
    Модель курса лечения Табекс.
    
    Attributes:
        course_id: Внутренний ID курса лечения
        user_id: ID пользователя (связь с таблицей users)
        start_date: Дата начала курса лечения
        current_phase: Текущая фаза лечения (1-5)
        current_character: Текущий активный персонаж
        status: Статус курса (active/completed/failed/paused)
        smoking_quit_date: Дата полного отказа от курения (5-й день)
        created_at: Время создания записи
        updated_at: Время последнего обновления
    """
    course_id: Optional[int]
    user_id: int
    start_date: date
    current_phase: int = 1
    current_character: str = 'gaspode'
    status: str = TreatmentStatus.ACTIVE.value
    smoking_quit_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Валидация данных после создания объекта."""
        # Проверяем корректность фазы
        if not 1 <= self.current_phase <= 5:
            raise ValueError("Фаза лечения должна быть от 1 до 5")
        
        # Проверяем корректность статуса
        valid_statuses = [status.value for status in TreatmentStatus]
        if self.status not in valid_statuses:
            raise ValueError(f"Статус должен быть одним из: {valid_statuses}")
        
        # Проверяем корректность персонажа
        valid_characters = ['gaspode', 'nobby_colon', 'angua', 'carrot', 'vimes', 'vetinari', 'death']
        if self.current_character not in valid_characters:
            raise ValueError(f"Персонаж должен быть одним из: {valid_characters}")
        
        # Устанавливаем время создания, если не задано
        if self.created_at is None:
            self.created_at = datetime.now()
        
        if self.updated_at is None:
            self.updated_at = self.created_at
    
    @property
    def days_since_start(self) -> int:
        """Количество дней с начала курса."""
        return (date.today() - self.start_date).days + 1
    
    @property
    def is_active(self) -> bool:
        """Проверка, активен ли курс."""
        return self.status == TreatmentStatus.ACTIVE.value
    
    @property
    def is_completed(self) -> bool:
        """Проверка, завершен ли курс.""" 
        return self.status == TreatmentStatus.COMPLETED.value
    
    @property
    def is_failed(self) -> bool:
        """Проверка, провален ли курс."""
        return self.status == TreatmentStatus.FAILED.value
    
    def get_expected_character_for_day(self, day: int) -> str:
        """
        Определяет ожидаемого персонажа для конкретного дня лечения.
        
        Args:
            day: День лечения (1-25)
            
        Returns:
            Название персонажа для данного дня
        """
        if 1 <= day <= 3:
            return 'gaspode'
        elif 4 <= day <= 12:
            return 'nobby_colon'
        elif 13 <= day <= 16:
            return 'angua'
        elif 17 <= day <= 20:
            return 'carrot'
        elif 21 <= day <= 25:
            return 'vimes'
        elif day > 25:
            return 'vetinari'  # Финальная аудиенция
        else:
            raise ValueError(f"Некорректный день лечения: {day}")
    
    def get_expected_phase_for_day(self, day: int) -> int:
        """
        Определяет ожидаемую фазу для конкретного дня лечения.
        
        Args:
            day: День лечения (1-25)
            
        Returns:
            Номер фазы для данного дня
        """
        if 1 <= day <= 3:
            return 1
        elif 4 <= day <= 12:
            return 2
        elif 13 <= day <= 16:
            return 3
        elif 17 <= day <= 20:
            return 4
        elif 21 <= day <= 25:
            return 5
        else:
            raise ValueError(f"Некорректный день лечения: {day}")
    
    def should_quit_smoking_today(self) -> bool:
        """Проверяет, нужно ли сегодня полностью отказаться от курения (5-й день)."""
        return self.days_since_start == 5
    
    def __str__(self) -> str:
        return f"TreatmentCourse(id={self.course_id}, user_id={self.user_id}, day={self.days_since_start}, phase={self.current_phase}, character={self.current_character})"
