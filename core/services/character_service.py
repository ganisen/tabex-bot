"""
Сервис управления персонажами Плоского мира.

Определяет активного персонажа по дню лечения,
управляет переходами между персонажами,
предоставляет интерфейс для получения сообщений.
"""
import logging
from typing import Optional, Dict, List
from datetime import date

from core.characters.base_character import BaseCharacter
from core.characters.gaspode import gaspode
from core.characters.nobby_colon import nobby_colon  
from core.characters.angua import angua
from core.characters.carrot import carrot
from core.characters.vimes import vimes
from core.characters.vetinari import vetinari
from core.characters.death import death
from core.models.treatment import TreatmentCourse

logger = logging.getLogger(__name__)


class CharacterService:
    """
    Сервис управления персонажами Плоского мира.
    
    Отвечает за:
    - Определение активного персонажа по дню лечения
    - Переходы между персонажами при смене фаз
    - Получение персонализированных сообщений
    - Обработку сценариев неудачи (активация СМЕРТИ)
    """
    
    def __init__(self):
        """Инициализация сервиса с картой персонажей."""
        self.characters: Dict[str, BaseCharacter] = {
            'gaspode': gaspode,
            'nobby_colon': nobby_colon,
            'angua': angua, 
            'carrot': carrot,
            'vimes': vimes,
            'vetinari': vetinari,
            'death': death
        }
        logger.info("CharacterService инициализирован с персонажами: %s", 
                   list(self.characters.keys()))
    
    def get_character_for_day(self, day: int) -> BaseCharacter:
        """
        Определяет активного персонажа для указанного дня лечения.
        
        Args:
            day: День лечения (1-25+)
            
        Returns:
            Экземпляр персонажа для данного дня
        """
        if 1 <= day <= 3:
            return gaspode
        elif 4 <= day <= 12:
            return nobby_colon
        elif 13 <= day <= 16:
            return angua
        elif 17 <= day <= 20:
            return carrot
        elif 21 <= day <= 25:
            return vimes
        elif day >= 26:
            return vetinari
        else:
            logger.warning(f"Неверный день лечения: {day}, возвращаем Гаспода")
            return gaspode
    
    def get_character_by_name(self, name: str) -> Optional[BaseCharacter]:
        """
        Получает персонажа по имени.
        
        Args:
            name: Имя персонажа
            
        Returns:
            Экземпляр персонажа или None
        """
        character = self.characters.get(name)
        if not character:
            logger.warning(f"Персонаж '{name}' не найден")
        return character
    
    def get_current_character(self, course: TreatmentCourse) -> BaseCharacter:
        """
        Определяет текущего активного персонажа для курса лечения.
        
        Args:
            course: Курс лечения
            
        Returns:
            Текущий активный персонаж
        """
        current_day = course.days_since_start
        expected_character = course.get_expected_character_for_day(current_day)
        
        # Если текущий персонаж в курсе не соответствует ожидаемому - обновляем
        if course.current_character != expected_character:
            logger.info(f"Смена персонажа: {course.current_character} -> {expected_character} (день {current_day})")
            course.current_character = expected_character
        
        return self.get_character_by_name(course.current_character) or gaspode
    
    def should_transition_character(self, course: TreatmentCourse) -> bool:
        """
        Проверяет, нужна ли смена персонажа.
        
        Args:
            course: Курс лечения
            
        Returns:
            True, если нужна смена персонажа
        """
        current_day = course.days_since_start
        expected_character = course.get_expected_character_for_day(current_day)
        return course.current_character != expected_character
    
    def get_transition_messages(self, course: TreatmentCourse, user_name: str, user_gender: str) -> tuple[str, str]:
        """
        Получает сообщения для перехода между персонажами.
        
        Args:
            course: Курс лечения
            user_name: Имя пользователя
            user_gender: Пол пользователя
            
        Returns:
            Кортеж (прощальное_сообщение_старого, приветственное_сообщение_нового)
        """
        current_character = self.get_character_by_name(course.current_character)
        new_day = course.days_since_start
        expected_character_name = course.get_expected_character_for_day(new_day)
        new_character = self.get_character_by_name(expected_character_name)
        
        farewell_message = ""
        greeting_message = ""
        
        if current_character and current_character.name != "Death":
            farewell_message = current_character.get_farewell_message(user_name, user_gender)
        
        if new_character:
            greeting_message = new_character.get_greeting_message(user_name, user_gender)
        
        return farewell_message, greeting_message
    
    def activate_death_scenario(self, course: TreatmentCourse, user_name: str, user_gender: str, reason: str = "критические_нарушения") -> str:
        """
        Активирует сценарий неудачи с персонажем СМЕРТЬ.
        
        Args:
            course: Курс лечения
            user_name: Имя пользователя  
            user_gender: Пол пользователя
            reason: Причина активации СМЕРТИ
            
        Returns:
            Сообщение от СМЕРТИ
        """
        logger.warning(f"Активация сценария СМЕРТИ для курса {course.course_id}, причина: {reason}")
        
        # Обновляем статус курса
        course.current_character = 'death'
        course.status = 'failed'
        
        return death.get_greeting_message(user_name, user_gender)
    
    def get_all_characters(self) -> List[str]:
        """
        Получает список всех доступных персонажей.
        
        Returns:
            Список имен персонажей
        """
        return list(self.characters.keys())
    
    def get_character_info(self, character_name: str) -> Optional[dict]:
        """
        Получает информацию о персонаже.
        
        Args:
            character_name: Имя персонажа
            
        Returns:
            Словарь с информацией о персонаже
        """
        character = self.get_character_by_name(character_name)
        if not character:
            return None
        
        return {
            'name': character.name,
            'emoji': character.emoji,
            'phase_days': character.phase_days,
            'active_from': character.phase_days[0],
            'active_to': character.phase_days[1]
        }


# Глобальный экземпляр сервиса
character_service = CharacterService()
