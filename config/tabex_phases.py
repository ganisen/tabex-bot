"""
Конфигурация фаз лечения Табекс.

Определяет медицинские параметры каждой фазы лечения:
интервалы приёма, количество таблеток, персонажей и особые события.
"""
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from enum import Enum


class PhaseType(Enum):
    """Типы фаз лечения."""
    INITIAL = "initial"       # Начальная фаза
    INTENSIVE = "intensive"   # Интенсивная фаза  
    REDUCTION = "reduction"   # Фаза снижения
    MINIMAL = "minimal"       # Минимальная фаза
    COMPLETION = "completion" # Завершающая фаза


@dataclass
class TabexPhaseConfig:
    """
    Конфигурация одной фазы лечения Табекс.
    
    Attributes:
        phase_number: Номер фазы (1-5)
        day_range: Диапазон дней (start, end) включительно
        interval_hours: Интервал между приёмами в часах
        doses_per_day: Количество таблеток в день
        character: Активный персонаж для этой фазы
        phase_type: Тип фазы лечения
        special_events: Особые события в эти дни
        description: Описание фазы
    """
    phase_number: int
    day_range: Tuple[int, int]
    interval_hours: float
    doses_per_day: int
    character: str
    phase_type: PhaseType
    special_events: Dict[int, str]
    description: str
    
    def is_day_in_phase(self, day: int) -> bool:
        """Проверяет, входит ли день в эту фазу."""
        return self.day_range[0] <= day <= self.day_range[1]
    
    def get_special_event_for_day(self, day: int) -> Optional[str]:
        """Возвращает особое событие для дня, если есть."""
        return self.special_events.get(day)


# Конфигурация всех фаз лечения Табекс
TABEX_PHASES_CONFIG: Dict[int, TabexPhaseConfig] = {
    1: TabexPhaseConfig(
        phase_number=1,
        day_range=(1, 3),
        interval_hours=2.0,
        doses_per_day=6,
        character='gaspode',
        phase_type=PhaseType.INITIAL,
        special_events={
            1: "Начало программы исправления",
            3: "Переход под надзор стражников"
        },
        description="Начальная фаза: арест Гаспода, знакомство с программой. "
                   "6 таблеток в день каждые 2 часа."
    ),
    
    2: TabexPhaseConfig(
        phase_number=2,
        day_range=(4, 12),
        interval_hours=2.5,
        doses_per_day=5,
        character='nobby_colon',
        phase_type=PhaseType.INTENSIVE,
        special_events={
            4: "Передача стражникам Шнобби и Колону",
            5: "КРИТИЧЕСКИЙ ДЕНЬ: полный отказ от курения!",
            12: "Конец надзора дуэта стражников"
        },
        description="Интенсивная фаза: надзор Шнобби и Колона. "
                   "5 таблеток в день каждые 2.5 часа. "
                   "5-й день - обязательный полный отказ от курения!"
    ),
    
    3: TabexPhaseConfig(
        phase_number=3,
        day_range=(13, 16),
        interval_hours=3.0,
        doses_per_day=4,
        character='angua',
        phase_type=PhaseType.REDUCTION,
        special_events={
            13: "Передача констеблю Ангве",
            16: "Завершение надзора оборотня"
        },
        description="Фаза снижения: надзор Ангвы. "
                   "4 таблетки в день каждые 3 часа. "
                   "Обострённое чутьё на нарушения."
    ),
    
    4: TabexPhaseConfig(
        phase_number=4,
        day_range=(17, 20),
        interval_hours=5.0,
        doses_per_day=3,
        character='carrot',
        phase_type=PhaseType.MINIMAL,
        special_events={
            17: "Передача констеблю Моркоу",
            20: "Конец поддержки самого доброго стражника"
        },
        description="Минимальная фаза: поддержка Моркоу. "
                   "3 таблетки в день каждые 5 часов. "
                   "Максимальная вера в успех пациента."
    ),
    
    5: TabexPhaseConfig(
        phase_number=5, 
        day_range=(21, 25),
        interval_hours=8.0,  # Гибкий режим
        doses_per_day=2,     # 1-2 таблетки по потребности
        character='vimes',
        phase_type=PhaseType.COMPLETION,
        special_events={
            21: "Передача капитану Ваймсу",
            25: "Завершение программы",
            26: "Подготовка к аудиенции у Витинари"
        },
        description="Завершающая фаза: контроль Ваймса. "
                   "1-2 таблетки в день по потребности. "
                   "Подготовка к финальной аудиенции."
    )
}


class TabexPhaseManager:
    """
    Менеджер фаз лечения Табекс.
    
    Управляет переходами между фазами, определяет текущую фазу
    и предоставляет информацию о режиме приёма.
    """
    
    def __init__(self):
        """Инициализация менеджера фаз."""
        self.phases = TABEX_PHASES_CONFIG
    
    def get_phase_for_day(self, day: int) -> Optional[TabexPhaseConfig]:
        """
        Определяет фазу лечения для указанного дня.
        
        Args:
            day: День лечения (1-25)
            
        Returns:
            Конфигурация фазы или None для недопустимых дней
        """
        for phase in self.phases.values():
            if phase.is_day_in_phase(day):
                return phase
        return None
    
    def get_current_phase(self, current_day: int) -> TabexPhaseConfig:
        """
        Получает текущую фазу с обработкой ошибок.
        
        Args:
            current_day: Текущий день лечения
            
        Returns:
            Конфигурация фазы (по умолчанию - фаза 1)
        """
        phase = self.get_phase_for_day(current_day)
        return phase or self.phases[1]  # По умолчанию первая фаза
    
    def should_transition_phase(self, current_day: int, current_phase_number: int) -> bool:
        """
        Проверяет, нужен ли переход в новую фазу.
        
        Args:
            current_day: Текущий день лечения
            current_phase_number: Текущий номер фазы
            
        Returns:
            True, если нужен переход в новую фазу
        """
        expected_phase = self.get_phase_for_day(current_day)
        if not expected_phase:
            return False
        return expected_phase.phase_number != current_phase_number
    
    def get_next_dose_time_slots(self, phase: TabexPhaseConfig, start_time: str) -> list[str]:
        """
        Рассчитывает все временные слоты приёма для фазы на один день.
        
        Args:
            phase: Конфигурация фазы
            start_time: Время первого приёма в формате "HH:MM"
            
        Returns:
            Список времён приёма в формате ["HH:MM", ...]
        """
        from datetime import datetime, timedelta
        
        try:
            # Парсим начальное время
            start_dt = datetime.strptime(start_time, "%H:%M")
            
            # Генерируем все слоты на день
            slots = []
            current_time = start_dt
            
            for i in range(phase.doses_per_day):
                slots.append(current_time.strftime("%H:%M"))
                
                # Добавляем интервал для следующего слота
                if i < phase.doses_per_day - 1:  # Не добавляем интервал после последней дозы
                    interval_minutes = int(phase.interval_hours * 60)
                    current_time += timedelta(minutes=interval_minutes)
            
            return slots
            
        except ValueError:
            # В случае ошибки возвращаем базовые слоты
            return [start_time]
    
    def get_special_event_for_day(self, day: int) -> Optional[str]:
        """
        Получает особое событие для указанного дня.
        
        Args:
            day: День лечения
            
        Returns:
            Описание особого события или None
        """
        phase = self.get_phase_for_day(day)
        if not phase:
            return None
        return phase.get_special_event_for_day(day)
    
    def is_critical_day(self, day: int) -> bool:
        """
        Проверяет, является ли день критическим (5-й день - отказ от курения).
        
        Args:
            day: День лечения
            
        Returns:
            True, если это критический день
        """
        return day == 5
    
    def get_phase_summary(self) -> Dict[int, str]:
        """
        Возвращает краткое описание всех фаз.
        
        Returns:
            Словарь {номер_фазы: краткое_описание}
        """
        return {
            phase.phase_number: f"Дни {phase.day_range[0]}-{phase.day_range[1]}: "
                               f"{phase.doses_per_day} таб./день, "
                               f"каждые {phase.interval_hours}ч ({phase.character})"
            for phase in self.phases.values()
        }


# Глобальный экземпляр менеджера фаз
phase_manager = TabexPhaseManager()
