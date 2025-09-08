"""
Сервис напоминаний с персонажами Плоского мира.

Интегрирован с системой персонажей, поддерживает автоматическое
подтягивание пропущенных доз, отправляет персонализированные напоминания
с inline-кнопками для взаимодействия.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ContextTypes

from core.services.character_service import character_service
from core.services.schedule_service import schedule_service, DoseSchedule
from core.models.treatment import TreatmentCourse
from core.models.user import User
from core.models.tabex_log import TabexLog, TabexLogStatus
from database.repositories import TreatmentRepository, TabexRepository, UserRepository

logger = logging.getLogger(__name__)


class ReminderService:
    """
    Сервис напоминаний от персонажей Плоского мира.
    
    Отвечает за:
    - Отправку персонализированных напоминаний от текущего персонажа
    - Автоматическое подтягивание пропущенных доз
    - Создание inline-клавиатур для взаимодействия  
    - Escalation при множественных пропусках
    - Интеграцию с системой фаз и персонажей
    """
    
    def __init__(self):
        """Инициализация сервиса напоминаний."""
        self.active_users: Dict[int, bool] = {}
        self.reminder_tasks: Dict[int, asyncio.Task] = {}
        self.postponed_reminders: Dict[int, datetime] = {}
        self.last_reminder_sent: Dict[str, datetime] = {}  # Ключ: f"{user_id}_{dose_timestamp}"
        
        # Репозитории
        self.treatment_repo = TreatmentRepository()
        self.tabex_repo = TabexRepository()
        self.user_repo = UserRepository()
        
        logger.info("ReminderService инициализирован с поддержкой персонажей")
    
    async def start_reminders_for_user(self, user_id: int, first_dose_time: str, bot: Bot) -> bool:
        """
        Запускает напоминания для пользователя с автоподтягиванием.
        
        Args:
            user_id: Telegram ID пользователя
            first_dose_time: Время первой дозы в формате "HH:MM"
            bot: Экземпляр Telegram бота
            
        Returns:
            True, если напоминания успешно запущены
        """
        try:
            # Получаем данные пользователя и курса
            user_obj = await self.user_repo.get_by_telegram_id(user_id)
            if not user_obj:
                logger.error(f"Пользователь {user_id} не найден")
                return False
            
            course = await self.treatment_repo.get_active_by_user_id(user_obj.user_id)
            if not course:
                logger.error(f"Активный курс для пользователя {user_id} не найден")
                return False
            
            # Останавливаем существующие напоминания, если есть
            await self.stop_reminders_for_user(user_id)
            
            # Активируем напоминания
            self.active_users[user_id] = True
            
            # Запускаем основной цикл напоминаний
            task = asyncio.create_task(
                self._reminder_loop(user_id, user_obj, course, first_dose_time, bot)
            )
            self.reminder_tasks[user_id] = task
            
            logger.info(f"Напоминания запущены для пользователя {user_id} с времени {first_dose_time}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при запуске напоминаний для {user_id}: {e}")
            return False
    
    async def stop_reminders_for_user(self, user_id: int) -> None:
        """
        Останавливает напоминания для пользователя.
        
        Args:
            user_id: Telegram ID пользователя
        """
        try:
            self.active_users[user_id] = False
            
            # Отменяем задачу напоминаний
            if user_id in self.reminder_tasks:
                task = self.reminder_tasks[user_id]
                task.cancel()
                del self.reminder_tasks[user_id]
            
            # Очищаем отложенные напоминания
            if user_id in self.postponed_reminders:
                del self.postponed_reminders[user_id]
            
            # Очищаем историю отправленных напоминаний для этого пользователя
            keys_to_remove = [key for key in self.last_reminder_sent.keys() if key.startswith(f"{user_id}_")]
            for key in keys_to_remove:
                del self.last_reminder_sent[key]
            
            logger.info(f"Напоминания остановлены для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при остановке напоминаний для {user_id}: {e}")
    
    async def _reminder_loop(self, user_id: int, user_obj: User, course: TreatmentCourse, first_dose_time: str, bot: Bot) -> None:
        """
        Основной цикл напоминаний для пользователя.
        
        Args:
            user_id: Telegram ID пользователя
            user_obj: Объект пользователя
            course: Курс лечения
            first_dose_time: Время первой дозы
            bot: Экземпляр бота
        """
        try:
            while self.active_users.get(user_id, False):
                # Получаем актуальные данные курса
                current_course = await self.treatment_repo.get_by_id(course.course_id)
                if not current_course or not current_course.is_active:
                    logger.info(f"Курс завершен для пользователя {user_id}")
                    break
                
                # Получаем логи приёмов
                existing_logs = await self.tabex_repo.get_logs_by_course_id(course.course_id)
                
                # Проверяем, есть ли отложенное напоминание
                if user_id in self.postponed_reminders:
                    postponed_time = self.postponed_reminders[user_id]
                    now = datetime.now()
                    
                    if now >= postponed_time:
                        # Время пришло - отправляем отложенное напоминание
                        original_dose_time = self.postponed_reminders.get(f"{user_id}_original_time")
                        del self.postponed_reminders[user_id]
                        if f"{user_id}_original_time" in self.postponed_reminders:
                            del self.postponed_reminders[f"{user_id}_original_time"]
                        
                        await self._send_postponed_reminder(user_id, user_obj, current_course, original_dose_time, bot)
                        
                        # После отложенного напоминания переходим к следующей итерации
                        await asyncio.sleep(60)  # Проверяем каждую минуту
                        continue
                    else:
                        # Ждём до времени отложенного напоминания
                        wait_seconds = (postponed_time - now).total_seconds()
                        if wait_seconds > 0:
                            logger.info(f"Ждём {wait_seconds/60:.1f} минут до отложенного напоминания для {user_id}")
                            # Ждём максимум 1 минуту, чтобы не блокировать цикл слишком долго
                            await asyncio.sleep(min(wait_seconds, 60))
                            continue
                
                # Получаем следующую дозу для напоминания  
                next_dose_time = schedule_service.get_next_dose_time(current_course, first_dose_time, existing_logs)
                
                if not next_dose_time:
                    logger.info(f"Нет следующих доз для пользователя {user_id}")
                    break
                
                # Ждём до времени напоминания
                now = datetime.now()
                if next_dose_time > now:
                    wait_seconds = (next_dose_time - now).total_seconds()
                    logger.info(f"Ждём {wait_seconds/60:.1f} минут до следующего напоминания для {user_id}")
                    # Ждём максимум 1 минуту, чтобы не блокировать проверку отложенных напоминаний
                    await asyncio.sleep(min(wait_seconds, 60))
                    continue
                
                # Проверяем, что пользователь всё ещё активен
                if not self.active_users.get(user_id, False):
                    break
                
                # Проверяем, можно ли отправить напоминание (интервал 15 минут)
                dose_key = f"{user_id}_{int(next_dose_time.timestamp())}"
                now = datetime.now()
                last_sent = self.last_reminder_sent.get(dose_key)
                
                can_send_reminder = (
                    last_sent is None or 
                    (now - last_sent).total_seconds() >= 15 * 60  # 15 минут
                )
                
                if can_send_reminder:
                    # Отправляем напоминание
                    await self._send_dose_reminder(user_id, user_obj, current_course, next_dose_time, bot)
                    
                    # Записываем время отправки
                    self.last_reminder_sent[dose_key] = now
                    
                    # Запускаем таймер автоматического пропуска только для первого напоминания
                    if last_sent is None:
                        asyncio.create_task(
                            self._schedule_auto_miss(user_id, user_obj, current_course, next_dose_time, bot)
                        )
                else:
                    # Если нельзя отправить - просто логируем
                    minutes_left = 15 - int((now - last_sent).total_seconds() / 60)
                    logger.debug(f"Повторное напоминание для {user_id} через {minutes_left} минут")
                
                # Пауза перед следующей итерацией
                await asyncio.sleep(60)  # Проверяем каждую минуту
                
        except asyncio.CancelledError:
            logger.info(f"Цикл напоминаний отменен для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка в цикле напоминаний для {user_id}: {e}")
    
    async def _send_dose_reminder(self, user_id: int, user_obj: User, course: TreatmentCourse, dose_time: datetime, bot: Bot) -> None:
        """
        Отправляет напоминание о дозе от текущего персонажа.
        
        Args:
            user_id: Telegram ID пользователя
            user_obj: Объект пользователя
            course: Курс лечения
            dose_time: Время дозы
            bot: Экземпляр бота
        """
        try:
            # Определяем текущего персонажа
            current_character = character_service.get_current_character(course)
            current_day = course.days_since_start
            
            # Определяем номер дозы в дне - используем реальное время первой дозы пользователя
            # Получаем время первой дозы из логов (самая ранняя доза курса)
            first_dose_time = "09:00"  # Значение по умолчанию
            existing_logs = await self.tabex_repo.get_logs_by_course_id(course.course_id)
            if existing_logs:
                earliest_log = min(existing_logs, key=lambda x: x.scheduled_time)
                first_dose_time = earliest_log.scheduled_time.strftime("%H:%M")
            
            daily_schedule = schedule_service.calculate_daily_schedule(course, first_dose_time, current_day)
            dose_number = 1
            for i, schedule in enumerate(daily_schedule):
                if schedule.scheduled_time.time() == dose_time.time():
                    dose_number = i + 1
                    break
            
            # Получаем сообщение от персонажа
            reminder_message = current_character.get_reminder_message(
                user_obj.first_name,
                user_obj.gender,
                dose_number,
                current_day
            )
            
            # Создаем inline-клавиатуру
            keyboard = self._create_dose_keyboard(course.course_id, dose_time)
            
            # Отправляем напоминание
            await bot.send_message(
                chat_id=user_id,
                text=reminder_message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            # Создаем запись в логе как запланированную
            tabex_log = TabexLog(
                log_id=None,
                course_id=course.course_id,
                scheduled_time=dose_time,
                status=TabexLogStatus.SCHEDULED.value,
                phase=course.current_phase
            )
            await self.tabex_repo.create_log(tabex_log)
            
            logger.info(f"Отправлено напоминание от {current_character.name} пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
    
    def _create_dose_keyboard(self, course_id: int, dose_time: datetime) -> InlineKeyboardMarkup:
        """
        Создает inline-клавиатуру для взаимодействия с напоминанием.
        
        Args:
            course_id: ID курса лечения
            dose_time: Время дозы
            
        Returns:
            Inline-клавиатура с кнопками действий
        """
        # Формат callback_data: action_courseId_timestamp
        timestamp = int(dose_time.timestamp())
        
        keyboard = [
            [InlineKeyboardButton("✅ ТАБЛЕТКА ПРИНЯТА", 
                                callback_data=f"dose_taken_{course_id}_{timestamp}")],
            [InlineKeyboardButton("⏰ ОТЛОЖИТЬ НА 5 МИН", 
                                callback_data=f"dose_postpone_{course_id}_{timestamp}")],
            [InlineKeyboardButton("❌ ПРОПУСК", 
                                callback_data=f"dose_skip_{course_id}_{timestamp}")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_dose_taken(self, user_id: int, course_id: int, dose_timestamp: int, bot: Bot) -> str:
        """
        Обрабатывает подтверждение приёма таблетки.
        
        Args:
            user_id: Telegram ID пользователя
            course_id: ID курса лечения  
            dose_timestamp: Timestamp запланированной дозы
            bot: Экземпляр бота
            
        Returns:
            Ответное сообщение от персонажа
        """
        try:
            # Получаем данные
            user_obj = await self.user_repo.get_by_telegram_id(user_id)
            course = await self.treatment_repo.get_by_id(course_id)
            dose_time = datetime.fromtimestamp(dose_timestamp)
            
            if not user_obj or not course:
                return "❌ Ошибка: данные не найдены"
            
            # Получаем и обновляем лог дозы
            tabex_log = await self._find_log_by_course_and_time(course_id, dose_time)
            if tabex_log:
                tabex_log.mark_taken()
                await self.tabex_repo.update_log(tabex_log)
            
            # Получаем ответ от персонажа
            current_character = character_service.get_current_character(course)
            response = current_character.get_dose_taken_response(user_obj.first_name, user_obj.gender)
            
            # Очищаем запись о напоминании для этой дозы
            dose_key = f"{user_id}_{dose_timestamp}"
            if dose_key in self.last_reminder_sent:
                del self.last_reminder_sent[dose_key]
            
            logger.info(f"Пользователь {user_id} принял дозу в {dose_time}")
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при обработке принятой дозы: {e}")
            return "❌ Произошла ошибка при обработке"
    
    async def handle_dose_postpone(self, user_id: int, course_id: int, dose_timestamp: int, bot: Bot) -> str:
        """
        Обрабатывает отсрочку дозы на 5 минут.
        
        Args:
            user_id: Telegram ID пользователя
            course_id: ID курса лечения
            dose_timestamp: Timestamp запланированной дозы
            bot: Экземпляр бота
            
        Returns:
            Ответное сообщение от персонажа
        """
        try:
            user_obj = await self.user_repo.get_by_telegram_id(user_id)
            course = await self.treatment_repo.get_by_id(course_id)
            
            if not user_obj or not course:
                return "❌ Ошибка: данные не найдены"
            
            # Сохраняем оригинальное время дозы
            original_dose_time = datetime.fromtimestamp(dose_timestamp)
            
            # Устанавливаем отложенное напоминание
            postponed_time = datetime.now() + timedelta(minutes=5)
            self.postponed_reminders[user_id] = postponed_time
            self.postponed_reminders[f"{user_id}_original_time"] = original_dose_time
            
            # Получаем ответ от персонажа
            current_character = character_service.get_current_character(course)
            response = current_character.get_dose_postponed_response(user_obj.first_name, user_obj.gender)
            
            # Сбрасываем время последнего напоминания для этой дозы, 
            # чтобы отсроченное напоминание могло быть отправлено
            dose_key = f"{user_id}_{dose_timestamp}"
            if dose_key in self.last_reminder_sent:
                del self.last_reminder_sent[dose_key]
            
            logger.info(f"Пользователь {user_id} отложил дозу на 5 минут (оригинальное время: {original_dose_time})")
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при обработке отсрочки дозы: {e}")
            return "❌ Произошла ошибка при обработке"
    
    async def handle_dose_skip(self, user_id: int, course_id: int, dose_timestamp: int, bot: Bot) -> str:
        """
        Обрабатывает пропуск дозы.
        
        Args:
            user_id: Telegram ID пользователя
            course_id: ID курса лечения
            dose_timestamp: Timestamp запланированной дозы
            bot: Экземпляр бота
            
        Returns:
            Ответное сообщение от персонажа (может включать предупреждение)
        """
        try:
            user_obj = await self.user_repo.get_by_telegram_id(user_id)
            course = await self.treatment_repo.get_by_id(course_id)
            dose_time = datetime.fromtimestamp(dose_timestamp)
            
            if not user_obj or not course:
                return "❌ Ошибка: данные не найдены"
            
            # Получаем и обновляем лог дозы
            tabex_log = await self._find_log_by_course_and_time(course_id, dose_time)
            if tabex_log:
                tabex_log.mark_skipped()
                await self.tabex_repo.update_log(tabex_log)
            
            # Получаем количество пропусков для статистики
            all_logs = await self.tabex_repo.get_logs_by_course_id(course_id)
            missed_count = sum(1 for log in all_logs if log.is_missed or log.is_skipped)
            
            # Получаем ответ от персонажа  
            current_character = character_service.get_current_character(course)
            
            # Реакция персонажа на пропуск (без активации СМЕРТИ)
            if missed_count > 3:
                response = current_character.get_warning_message(user_obj.first_name, user_obj.gender, missed_count)
            elif missed_count > 1:
                response = current_character.get_warning_message(user_obj.first_name, user_obj.gender, missed_count)
            else:
                response = current_character.get_dose_skipped_response(user_obj.first_name, user_obj.gender)
            
            # Очищаем запись о напоминании для этой дозы
            dose_key = f"{user_id}_{dose_timestamp}"
            if dose_key in self.last_reminder_sent:
                del self.last_reminder_sent[dose_key]
            
            logger.info(f"Пользователь {user_id} пропустил дозу в {dose_time} (всего пропусков: {missed_count})")
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при обработке пропуска дозы: {e}")
            return "❌ Произошла ошибка при обработке"
    
    async def _send_postponed_reminder(self, user_id: int, user_obj: User, course: TreatmentCourse, original_dose_time: datetime, bot: Bot) -> None:
        """
        Отправляет отложенное напоминание.
        
        Args:
            user_id: Telegram ID пользователя
            user_obj: Объект пользователя
            course: Курс лечения
            original_dose_time: Оригинальное время дозы
            bot: Экземпляр бота
        """
        try:
            current_character = character_service.get_current_character(course)
            
            message = f"{current_character.emoji} **Напоминание через 5 минут!**\n\n" \
                     f"{user_obj.first_name}, время принимать таблетку!\n\n" \
                     f"*\"Отсрочка закончилась. Пора действовать!\"*\n\n" \
                     f"— {current_character.name}"
            
            # Используем оригинальное время дозы для callback'ов
            original_timestamp = int(original_dose_time.timestamp()) if original_dose_time else int(datetime.now().timestamp())
            
            # Создаем упрощенную клавиатуру (без повторной отсрочки)
            keyboard = [
                [InlineKeyboardButton("✅ ТАБЛЕТКА ПРИНЯТА", 
                                    callback_data=f"dose_taken_{course.course_id}_{original_timestamp}")],
                [InlineKeyboardButton("❌ ПРОПУСК", 
                                    callback_data=f"dose_skip_{course.course_id}_{original_timestamp}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлено отложенное напоминание пользователю {user_id} (оригинальное время: {original_dose_time})")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке отложенного напоминания: {e}")
    
    async def _schedule_auto_miss(self, user_id: int, user_obj: User, course: TreatmentCourse, dose_time: datetime, bot: Bot) -> None:
        """
        Планирует автоматический пропуск дозы через половину времени до следующей.
        
        Args:
            user_id: Telegram ID пользователя
            user_obj: Объект пользователя
            course: Курс лечения
            dose_time: Время текущей дозы
            bot: Экземпляр бота
        """
        try:
            # Получаем конфигурацию текущей фазы
            from config.tabex_phases import phase_manager
            
            phase_config = phase_manager.get_phase_for_day(course.days_since_start)
            if not phase_config:
                return
            
            # Вычисляем время автоматического пропуска (половина интервала до следующей дозы)
            interval_hours = phase_config.interval_hours
            auto_miss_delay_hours = interval_hours / 2
            auto_miss_time = dose_time + timedelta(hours=auto_miss_delay_hours)
            
            # Ждём до времени автоматического пропуска
            now = datetime.now()
            if auto_miss_time > now:
                wait_seconds = (auto_miss_time - now).total_seconds()
                await asyncio.sleep(wait_seconds)
            
            # Проверяем, что пользователь все еще активен и доза не принята
            if not self.active_users.get(user_id, False):
                return
            
            # Проверяем, принял ли пользователь дозу
            tabex_log = await self._find_log_by_course_and_time(course.course_id, dose_time)
            if tabex_log and tabex_log.is_taken:
                return  # Доза уже принята
            
            # Автоматически отмечаем дозу как пропущенную
            if tabex_log:
                tabex_log.mark_missed(f"Автопропуск через {auto_miss_delay_hours:.1f}ч")
                await self.tabex_repo.update_log(tabex_log)
                
                logger.info(f"Доза автоматически помечена как пропущенная для пользователя {user_id} в {dose_time}")
            
        except Exception as e:
            logger.error(f"Ошибка при планировании автопропуска для {user_id}: {e}")
    
    async def _find_log_by_course_and_time(self, course_id: int, dose_time: datetime) -> Optional[TabexLog]:
        """
        Находит запись приёма по course_id и времени дозы.
        
        Args:
            course_id: ID курса лечения
            dose_time: Время дозы
            
        Returns:
            TabexLog или None, если запись не найдена
        """
        try:
            # Получаем все логи для курса
            all_logs = await self.tabex_repo.get_logs_by_course_id(course_id)
            
            # Ищем лог с подходящим временем (с точностью до минуты)
            for log in all_logs:
                if (log.scheduled_time.date() == dose_time.date() and 
                    log.scheduled_time.hour == dose_time.hour and 
                    log.scheduled_time.minute == dose_time.minute):
                    return log
            
            logger.info(f"Лог не найден для курса {course_id} и времени {dose_time}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при поиске лога по времени: {e}")
            return None


# Глобальный экземпляр сервиса
reminder_service = ReminderService()