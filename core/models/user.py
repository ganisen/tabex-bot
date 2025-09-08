"""
Модель пользователя системы с поддержкой гендерной дифференциации.

Содержит основную информацию о пользователе, включая гендер для 
персонализированного взаимодействия с персонажами Плоского мира.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """
    Модель пользователя Табекс-бота.
    
    Attributes:
        user_id: Внутренний ID пользователя в системе
        telegram_id: ID пользователя в Telegram  
        first_name: Имя пользователя
        username: Имя пользователя в Telegram (может быть None)
        gender: Пол пользователя ('male' или 'female')
        timezone: Часовой пояс пользователя (по умолчанию Europe/Moscow)
        created_at: Время регистрации пользователя
        updated_at: Время последнего обновления данных
    """
    user_id: Optional[int]
    telegram_id: int
    first_name: str
    username: Optional[str]
    gender: str  # 'male' или 'female'
    timezone: str = 'Europe/Moscow'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Валидация данных после создания объекта."""
        # Проверяем корректность гендера
        valid_genders = ['male', 'female']
        if self.gender not in valid_genders:
            raise ValueError(f"Гендер должен быть одним из: {valid_genders}")
        
        # Устанавливаем время создания, если не задано
        if self.created_at is None:
            self.created_at = datetime.now()
        
        if self.updated_at is None:
            self.updated_at = self.created_at
    
    def is_male(self) -> bool:
        """Проверка, является ли пользователь мужчиной."""
        return self.gender == 'male'
    
    def is_female(self) -> bool:
        """Проверка, является ли пользователь женщиной."""
        return self.gender == 'female'
    
    def get_gender_display(self) -> str:
        """Возвращает читаемое представление гендера."""
        return "мужской" if self.is_male() else "женский"
    
    def __str__(self) -> str:
        return f"User(id={self.user_id}, telegram_id={self.telegram_id}, name={self.first_name}, gender={self.gender})"
