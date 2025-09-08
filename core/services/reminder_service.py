"""
Сервис напоминаний от Городской Стражи.

Капитан Ваймс лично контролирует соблюдение режима приёма таблеток
и отправляет напоминания каждые 2 часа.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class VimesReminderService:
    """
    Сервис напоминаний от капитана Ваймса.
    
    Отвечает за отправку напоминаний о приёме таблеток каждые 2 часа.
    """
    
    def __init__(self):
        """Инициализация службы напоминаний."""
        self.active_reminders: Dict[int, bool] = {}
        self.user_schedules: Dict[int, str] = {}
        logger.info("Капитан Ваймс готов к несению службы напоминаний")
    
    async def start_reminder_for_user(self, user_id: int, first_dose_time: str, context: ContextTypes.DEFAULT_TYPE):
        """
        Запуск напоминаний для пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
            first_dose_time: Время первого приёма в формате HH:MM
            context: Контекст Telegram бота для отправки сообщений
        """
        try:
            self.active_reminders[user_id] = True
            self.user_schedules[user_id] = first_dose_time
            
            logger.info(f"Капитан Ваймс начал патрулирование пользователя {user_id} с {first_dose_time}")
            
            # Планируем первое напоминание через 2 часа от первого приёма
            await self._schedule_next_reminder(user_id, first_dose_time, context)
            
        except Exception as e:
            logger.error(f"Ошибка при запуске напоминаний для пользователя {user_id}: {e}")
    
    async def stop_reminder_for_user(self, user_id: int):
        """
        Остановка напоминаний для пользователя.
        
        Args:
            user_id: ID пользователя в Telegram
        """
        try:
            self.active_reminders[user_id] = False
            if user_id in self.user_schedules:
                del self.user_schedules[user_id]
            
            logger.info(f"Капитан Ваймс прекратил патрулирование пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при остановке напоминаний для пользователя {user_id}: {e}")
    
    async def _schedule_next_reminder(self, user_id: int, base_time: str, context: ContextTypes.DEFAULT_TYPE):
        """
        Планирование следующего напоминания.
        
        Args:
            user_id: ID пользователя
            base_time: Базовое время в формате HH:MM
            context: Контекст бота
        """
        if not self.active_reminders.get(user_id, False):
            return
        
        try:
            # Рассчитываем время следующего напоминания (каждые 2 часа)
            now = datetime.now()
            base_dt = datetime.strptime(base_time, "%H:%M").time()
            
            # Находим следующий слот времени (кратный 2 часам от базового времени)
            next_reminder = datetime.combine(now.date(), base_dt)
            
            while next_reminder <= now:
                next_reminder += timedelta(hours=2)
            
            # Вычисляем задержку до следующего напоминания
            delay_seconds = (next_reminder - now).total_seconds()
            
            logger.info(f"Следующее напоминание для пользователя {user_id} в {next_reminder.strftime('%H:%M')} (через {delay_seconds/60:.1f} мин)")
            
            # Планируем отправку напоминания
            await asyncio.sleep(delay_seconds)
            
            if self.active_reminders.get(user_id, False):
                await self._send_reminder(user_id, context)
                # Планируем следующее напоминание
                await self._schedule_next_reminder(user_id, base_time, context)
        
        except Exception as e:
            logger.error(f"Ошибка при планировании напоминания для пользователя {user_id}: {e}")
    
    async def _send_reminder(self, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """
        Отправка напоминания пользователю.
        
        Args:
            user_id: ID пользователя
            context: Контекст бота
        """
        vimes_reminder = """
🏴‍☠️ **Городская Стража на связи!**

⏰ **Время принять таблетку Табекса.**

Капитан Ваймс напоминает: регулярность - основа успешного исправления. Без исключений, без отговорок, без "забыл".

📋 **Твои действия:**
1. Прими таблетку прямо сейчас
2. Ответь "принял" или "готово"  
3. Жди следующего патруля через 2 часа

*"Дисциплина - это выбор между тем, что ты хочешь сейчас, и тем, что ты хочешь больше всего."*

— Капитан Ваймс, Городская Стража Анк-Морпорка

**P.S.** Не заставляй меня посылать за тобой констебля Моркоу.
"""
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=vimes_reminder,
                parse_mode='Markdown'
            )
            logger.info(f"Капитан Ваймс отправил напоминание пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
    
    def get_active_reminders_count(self) -> int:
        """Получить количество активных напоминаний."""
        return sum(1 for active in self.active_reminders.values() if active)
    
    def is_user_active(self, user_id: int) -> bool:
        """Проверить, активны ли напоминания для пользователя."""
        return self.active_reminders.get(user_id, False)


# Глобальный экземпляр сервиса
vimes_service = VimesReminderService()
