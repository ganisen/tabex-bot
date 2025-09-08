"""
Сервис управления расписанием приёма таблеток Табекс.

Рассчитывает время приёма в зависимости от фазы лечения,
управляет автоматическим подтягиванием пропущенных напоминаний,
интегрируется с системой персонажей.
"""
import logging
from datetime import datetime, timedelta, time, date
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass

from config.tabex_phases import phase_manager, TabexPhaseConfig
from core.models.treatment import TreatmentCourse
from core.models.tabex_log import TabexLog, TabexLogStatus

logger = logging.getLogger(__name__)


@dataclass
class DoseSchedule:
    """
    Расписание одной дозы.
    
    Attributes:
        dose_number: Номер дозы в дне (1, 2, 3...)
        scheduled_time: Запланированное время приёма
        phase: Фаза лечения
        day: День лечения
        is_overdue: Просрочена ли доза
    """
    dose_number: int
    scheduled_time: datetime
    phase: int
    day: int
    is_overdue: bool = False


class ScheduleService:
    """
    Сервис управления расписанием приёма Табекс.
    
    Отвечает за:
    - Расчёт времени приёма по фазам лечения
    - Автоматическое подтягивание пропущенных доз
    - Генерацию расписания на день/период
    - Проверку просроченных приёмов
    """
    
    def __init__(self):
        """Инициализация сервиса расписания."""
        self.phase_manager = phase_manager
        logger.info("ScheduleService инициализирован")
    
    def calculate_daily_schedule(self, course: TreatmentCourse, first_dose_time: str, target_day: Optional[int] = None) -> List[DoseSchedule]:
        """
        Рассчитывает расписание приёма на указанный день.
        
        Args:
            course: Курс лечения
            first_dose_time: Время первой дозы в формате "HH:MM"
            target_day: День для расчёта (по умолчанию - текущий)
            
        Returns:
            Список расписаний доз на день
        """
        if target_day is None:
            target_day = course.days_since_start
        
        # Получаем конфигурацию фазы для этого дня
        phase_config = self.phase_manager.get_phase_for_day(target_day)
        if not phase_config:
            logger.warning(f"Не найдена фаза для дня {target_day}")
            return []
        
        # Рассчитываем временные слоты
        time_slots = self.phase_manager.get_next_dose_time_slots(phase_config, first_dose_time)
        
        # Создаем расписания доз
        schedules = []
        target_date = course.start_date + timedelta(days=target_day - 1)
        now = datetime.now()
        
        for i, time_slot in enumerate(time_slots):
            try:
                # Парсим время и создаем datetime для этого дня
                slot_time = datetime.strptime(time_slot, "%H:%M").time()
                scheduled_datetime = datetime.combine(target_date, slot_time)
                
                # Проверяем, просрочена ли доза
                is_overdue = scheduled_datetime < now and target_date <= date.today()
                
                dose_schedule = DoseSchedule(
                    dose_number=i + 1,
                    scheduled_time=scheduled_datetime,
                    phase=phase_config.phase_number,
                    day=target_day,
                    is_overdue=is_overdue
                )
                schedules.append(dose_schedule)
                
            except ValueError as e:
                logger.error(f"Ошибка при парсинге времени '{time_slot}': {e}")
                continue
        
        logger.info(f"Рассчитано расписание на день {target_day}: {len(schedules)} доз")
        return schedules
    
    def get_overdue_doses(self, course: TreatmentCourse, first_dose_time: str, existing_logs: List[TabexLog]) -> List[DoseSchedule]:
        """
        Находит все просроченные (пропущенные) дозы до текущего момента.
        
        Args:
            course: Курс лечения
            first_dose_time: Время первой дозы
            existing_logs: Существующие записи приёма
            
        Returns:
            Список просроченных доз
        """
        overdue_doses = []
        now = datetime.now()
        current_day = course.days_since_start
        
        # Получаем все обработанные дозы (принятые, пропущенные, пропущенные намеренно) для быстрого поиска
        processed_doses = {
            (log.scheduled_time.date(), log.scheduled_time.time()): log
            for log in existing_logs 
            if log.status in [TabexLogStatus.TAKEN.value, TabexLogStatus.MISSED.value, TabexLogStatus.SKIPPED.value]
        }
        
        # Проверяем каждый день от начала до текущего
        for day in range(1, current_day + 1):
            daily_schedule = self.calculate_daily_schedule(course, first_dose_time, day)
            
            for dose_schedule in daily_schedule:
                # Пропускаем будущие дозы
                if dose_schedule.scheduled_time > now:
                    continue
                
                # Проверяем, обработана ли доза (принята, пропущена или намеренно пропущена)
                dose_key = (dose_schedule.scheduled_time.date(), dose_schedule.scheduled_time.time())
                if dose_key not in processed_doses:
                    dose_schedule.is_overdue = True
                    overdue_doses.append(dose_schedule)
        
        logger.info(f"Найдено {len(overdue_doses)} просроченных доз для курса {course.course_id}")
        return overdue_doses
    
    def get_next_dose_time(self, course: TreatmentCourse, first_dose_time: str, existing_logs: List[TabexLog]) -> Optional[datetime]:
        """
        Определяет время следующей дозы с учетом пропущенных.
        
        Args:
            course: Курс лечения  
            first_dose_time: Время первой дозы
            existing_logs: Существующие записи
            
        Returns:
            Время следующей дозы или None, если курс завершен
        """
        # Сначала проверяем просроченные дозы
        overdue_doses = self.get_overdue_doses(course, first_dose_time, existing_logs)
        if overdue_doses:
            # Возвращаем самую раннюю просроченную дозу
            earliest_overdue = min(overdue_doses, key=lambda x: x.scheduled_time)
            logger.info(f"Следующая доза - просроченная: {earliest_overdue.scheduled_time}")
            return earliest_overdue.scheduled_time
        
        # Если нет просроченных, ищем следующую запланированную дозу
        now = datetime.now()
        current_day = course.days_since_start
        
        # Проверяем текущий день
        daily_schedule = self.calculate_daily_schedule(course, first_dose_time, current_day)
        for dose_schedule in daily_schedule:
            if dose_schedule.scheduled_time > now:
                logger.info(f"Следующая доза сегодня: {dose_schedule.scheduled_time}")
                return dose_schedule.scheduled_time
        
        # Проверяем следующий день (если курс не завершен)
        if current_day < 25:  # Максимальная длительность курса
            next_day_schedule = self.calculate_daily_schedule(course, first_dose_time, current_day + 1)
            if next_day_schedule:
                next_dose = next_day_schedule[0].scheduled_time
                logger.info(f"Следующая доза завтра: {next_dose}")
                return next_dose
        
        logger.info("Следующих доз не найдено - курс завершен")
        return None
    
    def create_catch_up_schedule(self, overdue_doses: List[DoseSchedule], interval_minutes: int = 30) -> List[DoseSchedule]:
        """
        Создает расписание для "подтягивания" просроченных доз.
        
        Args:
            overdue_doses: Список просроченных доз
            interval_minutes: Интервал между подтягиваемыми дозами в минутах
            
        Returns:
            Расписание подтягивания с обновленным временем
        """
        if not overdue_doses:
            return []
        
        now = datetime.now()
        catch_up_schedule = []
        
        # Сортируем по времени (самые старые первыми)
        sorted_doses = sorted(overdue_doses, key=lambda x: x.scheduled_time)
        
        current_time = now
        for i, dose in enumerate(sorted_doses):
            # Создаем копию с обновленным временем
            catch_up_dose = DoseSchedule(
                dose_number=dose.dose_number,
                scheduled_time=current_time,
                phase=dose.phase,
                day=dose.day,
                is_overdue=True
            )
            catch_up_schedule.append(catch_up_dose)
            
            # Добавляем интервал для следующей дозы
            current_time += timedelta(minutes=interval_minutes)
        
        logger.info(f"Создано расписание подтягивания для {len(catch_up_schedule)} доз")
        return catch_up_schedule
    
    def get_phase_transition_info(self, course: TreatmentCourse) -> Optional[Dict]:
        """
        Проверяет, нужен ли переход между фазами.
        
        Args:
            course: Курс лечения
            
        Returns:
            Информация о переходе или None
        """
        current_day = course.days_since_start
        current_phase = self.phase_manager.get_phase_for_day(current_day)
        
        if not current_phase:
            return None
        
        # Проверяем, изменилась ли фаза
        if course.current_phase != current_phase.phase_number:
            return {
                'from_phase': course.current_phase,
                'to_phase': current_phase.phase_number,
                'from_character': course.current_character,
                'to_character': current_phase.character,
                'day': current_day,
                'special_event': current_phase.get_special_event_for_day(current_day)
            }
        
        return None
    
    def is_critical_day_today(self, course: TreatmentCourse) -> bool:
        """
        Проверяет, является ли сегодня критическим днем (5-й день).
        
        Args:
            course: Курс лечения
            
        Returns:
            True, если сегодня 5-й день лечения
        """
        return course.days_since_start == 5
    
    def get_daily_dose_count(self, day: int) -> int:
        """
        Получает количество доз для указанного дня.
        
        Args:
            day: День лечения
            
        Returns:
            Количество доз в этот день
        """
        phase_config = self.phase_manager.get_phase_for_day(day)
        return phase_config.doses_per_day if phase_config else 0
    
    def validate_first_dose_time(self, time_str: str) -> bool:
        """
        Проверяет корректность формата времени первой дозы.
        
        Args:
            time_str: Время в формате "HH:MM"
            
        Returns:
            True, если формат корректный
        """
        try:
            datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False


# Глобальный экземпляр сервиса
schedule_service = ScheduleService()
