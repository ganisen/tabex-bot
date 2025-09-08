"""
Базовый класс для всех персонажей Плоского мира.

Определяет интерфейс взаимодействия персонажей с пользователями
и обеспечивает гендерно-зависимую генерацию текстов.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Типы сообщений персонажей."""
    GREETING = "greeting"
    REMINDER = "reminder"
    ENCOURAGEMENT = "encouragement" 
    WARNING = "warning"
    FAREWELL = "farewell"
    DOSE_TAKEN = "dose_taken"
    DOSE_MISSED = "dose_missed"
    PHASE_TRANSITION = "phase_transition"


class BaseCharacter(ABC):
    """
    Базовый класс для всех персонажей Плоского мира.
    
    Определяет общий интерфейс для взаимодействия с пользователями
    и предоставляет механизмы гендерной дифференциации текстов.
    """
    
    def __init__(self, name: str, phase_days: tuple, emoji: str):
        """
        Инициализация персонажа.
        
        Args:
            name: Имя персонажа (для логов и идентификации)
            phase_days: Диапазон дней, когда персонаж активен (например, (1, 3))
            emoji: Эмоджи персонажа для сообщений
        """
        self.name = name
        self.phase_days = phase_days
        self.emoji = emoji
        self.logger = logging.getLogger(f"character.{name.lower()}")
    
    @abstractmethod
    def get_greeting_message(self, user_name: str, user_gender: str) -> str:
        """
        Приветственное сообщение при первой встрече с персонажем.
        
        Args:
            user_name: Имя пользователя
            user_gender: Пол пользователя ('male' или 'female')
            
        Returns:
            Приветственное сообщение персонажа
        """
        pass
    
    @abstractmethod 
    def get_reminder_message(self, user_name: str, user_gender: str, dose_number: int, current_day: int) -> str:
        """
        Напоминание о приёме таблетки.
        
        Args:
            user_name: Имя пользователя
            user_gender: Пол пользователя
            dose_number: Номер дозы в текущем дне (1, 2, 3...)
            current_day: Текущий день лечения
            
        Returns:
            Сообщение-напоминание от персонажа
        """
        pass
    
    @abstractmethod
    def get_encouragement_message(self, user_name: str, user_gender: str, progress_percent: int) -> str:
        """
        Поощрительное сообщение за хорошую дисциплину.
        
        Args:
            user_name: Имя пользователя
            user_gender: Пол пользователя
            progress_percent: Процент выполнения курса
            
        Returns:
            Поощрительное сообщение
        """
        pass
    
    @abstractmethod
    def get_warning_message(self, user_name: str, user_gender: str, missed_doses: int) -> str:
        """
        Предупреждение при пропуске приёмов.
        
        Args:
            user_name: Имя пользователя
            user_gender: Пол пользователя
            missed_doses: Количество пропущенных доз
            
        Returns:
            Предупреждающее сообщение
        """
        pass
    
    @abstractmethod
    def get_farewell_message(self, user_name: str, user_gender: str) -> str:
        """
        Прощальное сообщение при переходе к следующему персонажу.
        
        Args:
            user_name: Имя пользователя  
            user_gender: Пол пользователя
            
        Returns:
            Прощальное сообщение
        """
        pass
    
    def get_dose_taken_response(self, user_name: str, user_gender: str) -> str:
        """
        Реакция на подтверждение приёма таблетки.
        
        Args:
            user_name: Имя пользователя
            user_gender: Пол пользователя
            
        Returns:
            Положительная реакция персонажа
        """
        gender_pronoun = self._get_gender_pronoun(user_gender)
        return f"{self.emoji} **Хорошо, {gender_pronoun} {user_name}!**\n\nТаблетка принята, записано."
    
    def get_dose_postponed_response(self, user_name: str, user_gender: str) -> str:
        """
        Реакция на отсрочку приёма таблетки.
        
        Args:
            user_name: Имя пользователя
            user_gender: Пол пользователя
            
        Returns:
            Реакция на отсрочку
        """
        return f"{self.emoji} Ладно, напомню через 5 минут. Но не злоупотребляй!"
    
    def get_dose_skipped_response(self, user_name: str, user_gender: str) -> str:
        """
        Реакция на пропуск приёма таблетки.
        
        Args:
            user_name: Имя пользователя
            user_gender: Пол пользователя
            
        Returns:
            Негативная реакция на пропуск
        """
        gender_pronoun = self._get_gender_pronoun(user_gender)
        return f"{self.emoji} **{gender_pronoun.title()} {user_name}, это плохо!**\n\nПропуск зафиксирован. Больше так не делай."
    
    def _get_gender_pronoun(self, user_gender: str) -> str:
        """
        Возвращает гендерно-зависимое обращение.
        
        Args:
            user_gender: Пол пользователя
            
        Returns:
            "гражданин" для мужчин, "гражданка" для женщин
        """
        return "гражданин" if user_gender == 'male' else "гражданка"
    
    def _get_gender_ending(self, user_gender: str, male_ending: str = "", female_ending: str = "а") -> str:
        """
        Возвращает гендерное окончание для слов.
        
        Args:
            user_gender: Пол пользователя
            male_ending: Окончание для мужского рода
            female_ending: Окончание для женского рода
            
        Returns:
            Соответствующее окончание
        """
        return male_ending if user_gender == 'male' else female_ending
    
    def is_active_for_day(self, day: int) -> bool:
        """
        Проверяет, активен ли персонаж для указанного дня.
        
        Args:
            day: День лечения
            
        Returns:
            True, если персонаж активен в этот день
        """
        return self.phase_days[0] <= day <= self.phase_days[1]
    
    def __str__(self) -> str:
        return f"{self.name} (дни {self.phase_days[0]}-{self.phase_days[1]})"
