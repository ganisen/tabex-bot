"""
Репозитории для работы с базой данных Табекс-бота.

Содержит все репозитории для доступа к данным и CRUD операций
с пользователями, курсами лечения и записями приёма таблеток.
"""

from .user_repository import UserRepository
from .treatment_repository import TreatmentRepository
from .tabex_repository import TabexRepository

__all__ = [
    'UserRepository',
    'TreatmentRepository', 
    'TabexRepository',
]
