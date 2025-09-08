"""
Модель записи о приёме таблеток Табекс.

Отслеживает каждый запланированный и фактический приём таблеток,
включая реакции персонажей на действия пользователя.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class TabexLogStatus(Enum):
    """Статусы записи о приёме таблетки."""
    SCHEDULED = "scheduled"  # Запланирован
    TAKEN = "taken"         # Принят
    MISSED = "missed"       # Пропущен
    SKIPPED = "skipped"     # Пропущен намеренно


@dataclass
class TabexLog:
    """
    Модель записи о приёме таблетки Табекс.
    
    Attributes:
        log_id: Внутренний ID записи
        course_id: ID курса лечения (связь с treatment_courses)
        scheduled_time: Запланированное время приёма
        actual_time: Фактическое время приёма (может быть None)
        status: Статус записи (scheduled/taken/missed/skipped)
        phase: Фаза лечения на момент записи
        character_response: Ответ персонажа на действие пользователя
        created_at: Время создания записи
    """
    log_id: Optional[int]
    course_id: int
    scheduled_time: datetime
    actual_time: Optional[datetime] = None
    status: str = TabexLogStatus.SCHEDULED.value
    phase: int = 1
    character_response: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Валидация данных после создания объекта."""
        # Проверяем корректность статуса
        valid_statuses = [status.value for status in TabexLogStatus]
        if self.status not in valid_statuses:
            raise ValueError(f"Статус должен быть одним из: {valid_statuses}")
        
        # Проверяем корректность фазы
        if not 1 <= self.phase <= 5:
            raise ValueError("Фаза лечения должна быть от 1 до 5")
        
        # Устанавливаем время создания, если не задано
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def is_scheduled(self) -> bool:
        """Проверка, запланирован ли приём."""
        return self.status == TabexLogStatus.SCHEDULED.value
    
    @property
    def is_taken(self) -> bool:
        """Проверка, был ли приём выполнен."""
        return self.status == TabexLogStatus.TAKEN.value
    
    @property
    def is_missed(self) -> bool:
        """Проверка, был ли приём пропущен."""
        return self.status == TabexLogStatus.MISSED.value
    
    @property
    def is_skipped(self) -> bool:
        """Проверка, был ли приём пропущен намеренно."""
        return self.status == TabexLogStatus.SKIPPED.value
    
    @property
    def delay_minutes(self) -> Optional[int]:
        """Вычисляет задержку приёма в минутах."""
        if not self.actual_time:
            return None
        
        delay = self.actual_time - self.scheduled_time
        return int(delay.total_seconds() / 60)
    
    @property
    def is_delayed(self) -> bool:
        """Проверяет, был ли приём с задержкой."""
        delay = self.delay_minutes
        return delay is not None and delay > 15  # Задержка более 15 минут считается значимой
    
    @property
    def is_early(self) -> bool:
        """Проверяет, был ли приём раньше времени."""
        delay = self.delay_minutes
        return delay is not None and delay < -15  # Раньше на 15+ минут
    
    def mark_taken(self, actual_time: Optional[datetime] = None, character_response: str = "") -> None:
        """
        Отмечает приём как выполненный.
        
        Args:
            actual_time: Время фактического приёма (по умолчанию - текущее время)
            character_response: Реакция персонажа на приём
        """
        self.status = TabexLogStatus.TAKEN.value
        self.actual_time = actual_time or datetime.now()
        if character_response:
            self.character_response = character_response
    
    def mark_missed(self, character_response: str = "") -> None:
        """
        Отмечает приём как пропущенный.
        
        Args:
            character_response: Реакция персонажа на пропуск
        """
        self.status = TabexLogStatus.MISSED.value
        if character_response:
            self.character_response = character_response
    
    def mark_skipped(self, character_response: str = "") -> None:
        """
        Отмечает приём как намеренно пропущенный.
        
        Args:
            character_response: Реакция персонажа на пропуск
        """
        self.status = TabexLogStatus.SKIPPED.value
        if character_response:
            self.character_response = character_response
    
    def __str__(self) -> str:
        return f"TabexLog(id={self.log_id}, course_id={self.course_id}, scheduled={self.scheduled_time.strftime('%H:%M')}, status={self.status})"


@dataclass
class CharacterInteraction:
    """
    Модель взаимодействия с персонажем.
    
    Attributes:
        interaction_id: Внутренний ID взаимодействия
        course_id: ID курса лечения
        character_name: Имя персонажа
        interaction_type: Тип взаимодействия
        message_text: Текст сообщения от персонажа
        user_response: Ответ пользователя (может быть None)
        created_at: Время взаимодействия
    """
    interaction_id: Optional[int]
    course_id: int
    character_name: str
    interaction_type: str  # greeting, reminder, encouragement, warning, farewell
    message_text: str
    user_response: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Валидация данных после создания объекта."""
        valid_types = ['greeting', 'reminder', 'encouragement', 'warning', 'farewell']
        if self.interaction_type not in valid_types:
            raise ValueError(f"Тип взаимодействия должен быть одним из: {valid_types}")
        
        valid_characters = ['gaspode', 'nobby_colon', 'angua', 'carrot', 'vimes', 'vetinari', 'death']
        if self.character_name not in valid_characters:
            raise ValueError(f"Персонаж должен быть одним из: {valid_characters}")
        
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def __str__(self) -> str:
        return f"CharacterInteraction(id={self.interaction_id}, character={self.character_name}, type={self.interaction_type})"
