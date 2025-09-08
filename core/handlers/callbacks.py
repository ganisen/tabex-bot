"""
Обработчики callback-запросов от inline-кнопок Telegram-бота.

Обрабатывает все взаимодействия пользователей с inline-клавиатурами,
такие как подтверждение приёма таблеток, навигация по меню и настройки.
"""
import logging
from datetime import date
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from core.models.user import User
from core.models.treatment import TreatmentCourse
from core.services.reminder_service import reminder_service
from core.services.character_service import character_service
from database.repositories import UserRepository, TreatmentRepository

logger = logging.getLogger(__name__)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Универсальный обработчик callback-запросов от inline-кнопок.
    
    Маршрутизирует запросы к соответствующим обработчикам на основе
    данных callback (callback_data).
    """
    query = update.callback_query
    user = update.effective_user
    callback_data = query.data
    
    # Подтверждаем получение callback
    await query.answer()
    
    logger.info(f"Получен callback '{callback_data}' от пользователя {user.id} ({user.first_name})")
    
    try:
        # Обработка выбора гендера
        if callback_data.startswith("gender_"):
            await _handle_gender_selection(query, context, callback_data)
        
        # Обработка взаимодействий с дозами
        elif callback_data.startswith("dose_taken_"):
            await _handle_dose_taken(query, context, callback_data)
        elif callback_data.startswith("dose_postpone_"):
            await _handle_dose_postpone(query, context, callback_data)
        elif callback_data.startswith("dose_skip_"):
            await _handle_dose_skip(query, context, callback_data)
        
        # Обработка интерактивного опроса пропущенных доз
        elif callback_data.startswith("catchup_taken_"):
            await _handle_catchup_taken(query, context, callback_data)
        elif callback_data.startswith("catchup_missed_"):
            await _handle_catchup_missed(query, context, callback_data)
        elif callback_data.startswith("catchup_postpone_"):
            await _handle_catchup_postpone(query, context, callback_data)
        
        elif callback_data == "placeholder":
            await query.edit_message_text("🔧 Эта функция будет реализована в следующих версиях.")
        
        else:
            # Неизвестный callback
            await query.edit_message_text(
                f"❓ Неизвестное действие: {callback_data}\n\n"
                "Возможно, используется устаревшая версия интерфейса. "
                "Попробуйте перезапустить команду."
            )
            logger.warning(f"Неизвестный callback_data: {callback_data}")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке callback '{callback_data}': {e}")
        try:
            await query.edit_message_text(
                "🔧 Произошла ошибка при обработке запроса. "
                "Попробуйте позже или обратитесь к администратору."
            )
        except Exception:
            # Если даже отправка сообщения об ошибке не работает
            logger.error("Не удалось отправить сообщение об ошибке для callback")


async def _handle_dose_taken(query, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """
    Обработка подтверждения приёма таблетки.
    
    Args:
        query: Callback query от Telegram
        context: Контекст обработчика
        callback_data: Данные callback в формате "dose_taken_{course_id}_{timestamp}"
    """
    user = query.from_user
    
    try:
        # Парсим callback_data: dose_taken_123_1234567890
        parts = callback_data.split('_')
        if len(parts) != 3:
            logger.error(f"Некорректный формат callback_data: {callback_data}")
            await query.edit_message_text("❌ Ошибка обработки запроса")
            return
        
        course_id = int(parts[1])
        dose_timestamp = int(parts[2])
        
        # Обрабатываем через сервис напоминаний
        response = await reminder_service.handle_dose_taken(
            user.id, course_id, dose_timestamp, context.bot
        )
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка при обработке подтверждения дозы: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке")


async def _handle_dose_postpone(query, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """
    Обработка отсрочки дозы на 5 минут.
    
    Args:
        query: Callback query от Telegram
        context: Контекст обработчика
        callback_data: Данные callback в формате "dose_postpone_{course_id}_{timestamp}"
    """
    user = query.from_user
    
    try:
        # Парсим callback_data
        parts = callback_data.split('_')
        if len(parts) != 3:
            logger.error(f"Некорректный формат callback_data: {callback_data}")
            await query.edit_message_text("❌ Ошибка обработки запроса")
            return
        
        course_id = int(parts[1])
        dose_timestamp = int(parts[2])
        
        # Обрабатываем через сервис напоминаний
        response = await reminder_service.handle_dose_postpone(
            user.id, course_id, dose_timestamp, context.bot
        )
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка при обработке отсрочки дозы: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке")


async def _handle_dose_skip(query, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """
    Обработка пропуска дозы.
    
    Args:
        query: Callback query от Telegram
        context: Контекст обработчика
        callback_data: Данные callback в формате "dose_skip_{course_id}_{timestamp}"
    """
    user = query.from_user
    
    try:
        # Парсим callback_data
        parts = callback_data.split('_')
        if len(parts) != 3:
            logger.error(f"Некорректный формат callback_data: {callback_data}")
            await query.edit_message_text("❌ Ошибка обработки запроса")
            return
        
        course_id = int(parts[1])
        dose_timestamp = int(parts[2])
        
        # Обрабатываем через сервис напоминаний
        response = await reminder_service.handle_dose_skip(
            user.id, course_id, dose_timestamp, context.bot
        )
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка при обработке пропуска дозы: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке")


async def _handle_catchup_taken(query, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """
    Обработка подтверждения приёма дозы в режиме опроса.
    
    Args:
        query: Callback query от Telegram
        context: Контекст обработчика
        callback_data: Данные callback в формате "catchup_taken_{dose_index}"
    """
    user = query.from_user
    
    try:
        # Парсим callback_data: catchup_taken_0
        dose_index = int(callback_data.split('_')[2])
        
        # Получаем данные из контекста
        overdue_doses = context.user_data.get('overdue_doses', [])
        user_obj = context.user_data.get('user_obj')
        course_obj = context.user_data.get('course_obj')
        
        if not overdue_doses or not user_obj or not course_obj:
            await query.edit_message_text("❌ Ошибка: данные опроса не найдены")
            return
        
        if dose_index >= len(overdue_doses):
            await query.edit_message_text("❌ Ошибка: некорректный индекс дозы")
            return
        
        # Получаем дозу и создаем запись
        dose_schedule = overdue_doses[dose_index]
        
        from core.models.tabex_log import TabexLog, TabexLogStatus
        from database.repositories import TabexRepository
        
        tabex_repo = TabexRepository()
        
        # Создаем запись о принятой дозе
        tabex_log = TabexLog(
            log_id=None,
            course_id=course_obj.course_id,
            scheduled_time=dose_schedule.scheduled_time,
            actual_time=dose_schedule.scheduled_time,  # Условно в запланированное время
            status=TabexLogStatus.TAKEN.value,
            phase=dose_schedule.phase,
            character_response=f"Подтверждено в режиме опроса"
        )
        await tabex_repo.create(tabex_log)
        
        # Получаем персонажа для реакции
        current_character = character_service.get_current_character(course_obj)
        response = current_character.get_dose_taken_response(user_obj.first_name, user_obj.gender)
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
        # Переходим к следующей дозе или завершаем опрос
        await _continue_catchup_or_finish(query, context, dose_index)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке подтверждения дозы в опросе: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке")


async def _handle_catchup_missed(query, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """
    Обработка пропуска дозы в режиме опроса.
    """
    user = query.from_user
    
    try:
        dose_index = int(callback_data.split('_')[2])
        
        overdue_doses = context.user_data.get('overdue_doses', [])
        user_obj = context.user_data.get('user_obj')
        course_obj = context.user_data.get('course_obj')
        
        if not overdue_doses or not user_obj or not course_obj:
            await query.edit_message_text("❌ Ошибка: данные опроса не найдены")
            return
        
        if dose_index >= len(overdue_doses):
            await query.edit_message_text("❌ Ошибка: некорректный индекс дозы")
            return
        
        # Создаем запись о пропущенной дозе
        dose_schedule = overdue_doses[dose_index]
        
        from core.models.tabex_log import TabexLog, TabexLogStatus
        from database.repositories import TabexRepository
        
        tabex_repo = TabexRepository()
        
        tabex_log = TabexLog(
            log_id=None,
            course_id=course_obj.course_id,
            scheduled_time=dose_schedule.scheduled_time,
            status=TabexLogStatus.MISSED.value,
            phase=dose_schedule.phase,
            character_response=f"Пропущено (подтверждено в опросе)"
        )
        await tabex_repo.create(tabex_log)
        
        # Реакция персонажа
        current_character = character_service.get_current_character(course_obj)
        response = current_character.get_dose_skipped_response(user_obj.first_name, user_obj.gender)
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
        # Переходим дальше
        await _continue_catchup_or_finish(query, context, dose_index)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке пропуска дозы в опросе: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке")


async def _handle_catchup_postpone(query, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """
    Обработка отсрочки последней актуальной дозы на 5 минут.
    """
    user = query.from_user
    
    try:
        dose_index = int(callback_data.split('_')[2])
        
        overdue_doses = context.user_data.get('overdue_doses', [])
        user_obj = context.user_data.get('user_obj')
        course_obj = context.user_data.get('course_obj')
        first_dose_time = context.user_data.get('first_dose_time')
        
        if not overdue_doses or not user_obj or not course_obj:
            await query.edit_message_text("❌ Ошибка: данные опроса не найдены")
            return
        
        # Должна быть последняя доза для отсрочки
        if dose_index != len(overdue_doses) - 1:
            await query.edit_message_text("❌ Отсрочка доступна только для последней дозы")
            return
        
        # Завершаем опрос и запускаем обычный режим с отсрочкой
        current_character = character_service.get_current_character(course_obj)
        response = current_character.get_dose_postponed_response(user_obj.first_name, user_obj.gender)
        
        await query.edit_message_text(response, parse_mode='Markdown')
        
        # Создаем записи для всех доз кроме последней (они уже обработаны)
        await _finish_catchup_and_start_program(query, context, postpone_last=True)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке отсрочки дозы в опросе: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке")


async def _continue_catchup_or_finish(query, context: ContextTypes.DEFAULT_TYPE, current_dose_index: int) -> None:
    """
    Продолжает опрос или завершает его.
    """
    try:
        overdue_doses = context.user_data.get('overdue_doses', [])
        next_index = current_dose_index + 1
        
        # Если есть следующая доза - продолжаем опрос
        if next_index < len(overdue_doses):
            user_obj = context.user_data.get('user_obj')
            current_character = character_service.get_current_character(context.user_data.get('course_obj'))
            
            await _ask_about_next_dose(query, context, user_obj, overdue_doses[next_index], 
                                     next_index, len(overdue_doses), current_character)
        else:
            # Опрос завершен - запускаем обычный режим
            await _finish_catchup_and_start_program(query, context)
            
    except Exception as e:
        logger.error(f"Ошибка при продолжении опроса: {e}")


async def _ask_about_next_dose(query, context: ContextTypes.DEFAULT_TYPE,
                              user_obj: User, dose_schedule, dose_index: int, 
                              total_doses: int, current_character) -> None:
    """
    Задает вопрос о следующей дозе (для callback'ов).
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    try:
        gender_pronoun = "гражданин" if user_obj.is_male() else "гражданка"
        dose_time = dose_schedule.scheduled_time.strftime("%H:%M")
        
        # Определяем, это последняя доза или нет
        is_last_dose = (dose_index == total_doses - 1)
        
        question_message = f"""
{current_character.emoji} **Допрос #{dose_index + 1}/{total_doses}**

{gender_pronoun.title()} {user_obj.first_name}, что было в **{dose_time}**?

⏰ **Доза №{dose_schedule.dose_number} ({dose_schedule.day}-й день)**

Отвечай честно - {current_character.name} всё равно всё выяснит!

*"Правда выходит наружу рано или поздно."*
"""
        
        # Создаем кнопки
        buttons = []
        buttons.append([InlineKeyboardButton("✅ Принял(а)", callback_data=f"catchup_taken_{dose_index}")])
        buttons.append([InlineKeyboardButton("❌ Пропуск", callback_data=f"catchup_missed_{dose_index}")])
        
        # Для последней дозы добавляем вариант отсрочки
        if is_last_dose:
            buttons.append([InlineKeyboardButton("⏰ Отложить на 5 мин", callback_data=f"catchup_postpone_{dose_index}")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        # Отправляем новое сообщение (query.edit не подойдет для новой структуры)
        await query.message.reply_text(
            question_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка при задании вопроса о следующей дозе: {e}")


async def _finish_catchup_and_start_program(query, context: ContextTypes.DEFAULT_TYPE, postpone_last: bool = False) -> None:
    """
    Завершает режим опроса и запускает обычную программу.
    """
    try:
        from core.services.reminder_service import reminder_service
        
        user_obj = context.user_data.get('user_obj')
        course_obj = context.user_data.get('course_obj')
        first_dose_time = context.user_data.get('first_dose_time')
        
        if not user_obj or not course_obj or not first_dose_time:
            await query.message.reply_text("❌ Ошибка: данные для запуска программы не найдены")
            return
        
        # Очищаем режим опроса
        context.user_data['catchup_mode'] = False
        context.user_data.pop('overdue_doses', None)
        context.user_data.pop('current_catchup_index', None)
        
        # Получаем персонажа
        current_character = character_service.get_current_character(course_obj)
        gender_pronoun = "гражданин" if user_obj.is_male() else "гражданка"
        
        # Сообщение о завершении опроса
        completion_message = f"""
{current_character.emoji} **Допрос завершен, {gender_pronoun} {user_obj.first_name}!**

{current_character.name} записал все ответы. Теперь программа исправления работает в обычном режиме.

**Все пропущенные дозы учтены в статистике.**

{"⏰ Следующее напоминание через 5 минут (отсрочка)." if postpone_last else "⏰ Следующие напоминания по расписанию фаз."}

*"Прошлое учтено. Будущее зависит от тебя."*

— {current_character.name} (программа активирована)

**Используй /stats для контроля прогресса.**
"""
        
        await query.message.reply_text(
            completion_message,
            parse_mode='Markdown'
        )
        
        # Запускаем систему напоминаний
        success = await reminder_service.start_reminders_for_user(
            query.from_user.id, first_dose_time, context.bot
        )
        
        if postpone_last:
            # Если была отсрочка - устанавливаем напоминание через 5 минут
            from datetime import datetime, timedelta
            postponed_time = datetime.now() + timedelta(minutes=5)
            reminder_service.postponed_reminders[query.from_user.id] = postponed_time
        
        if success:
            logger.info(f"Напоминания запущены после опроса для пользователя {query.from_user.id}")
        else:
            logger.error(f"Ошибка запуска напоминаний после опроса для пользователя {query.from_user.id}")
            await query.message.reply_text(
                "⚠️ Произошла ошибка при запуске напоминаний. Попробуйте команду /start."
            )
            
    except Exception as e:
        logger.error(f"Ошибка при завершении опроса и запуске программы: {e}")


async def _handle_gender_selection(query, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """
    Обработка выбора гендера пользователем.
    
    Args:
        query: Callback query от Telegram
        context: Контекст обработчика
        callback_data: Данные callback в формате "gender_{male|female}_{user_id}"
    """
    user = query.from_user
    
    # Парсим callback_data: gender_male_123456 или gender_female_123456
    parts = callback_data.split('_')
    if len(parts) != 3:
        logger.error(f"Некорректный формат callback_data: {callback_data}")
        await query.edit_message_text("🐺 Рррр! Что-то пошло не так с протоколом!")
        return
    
    gender = parts[1]  # male или female
    expected_user_id = int(parts[2])
    
    # Проверяем, что callback от того же пользователя
    if user.id != expected_user_id:
        await query.answer("Это не твой выбор!", show_alert=True)
        return
    
    try:
        # Создаем пользователя в базе данных
        user_repo = UserRepository()
        
        new_user = User(
            user_id=None,
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
            gender=gender
        )
        
        created_user = await user_repo.create(new_user)
        
        # Создаем курс лечения
        treatment_repo = TreatmentRepository()
        
        new_course = TreatmentCourse(
            course_id=None,
            user_id=created_user.user_id,
            start_date=date.today(),
            current_phase=1,
            current_character='gaspode'
        )
        
        created_course = await treatment_repo.create(new_course)
        
        # Получаем персонажа для более точного сообщения
        current_character = character_service.get_character_by_name('gaspode')
        
        # Генерируем приветствие от Гаспода
        if current_character:
            gaspode_greeting = current_character.get_greeting_message(user.first_name, gender)
            
            # Добавляем инструкцию о времени
            time_instruction = f"""

📝 **А теперь введи время первой таблетки:**
Когда ты сегодня принял{'' if gender == 'male' else 'а'} первую таблетку Табекса?
Формат: **ЧЧ:ММ** (например: 08:30 или 14:15)

*"Регулярность - основа дисциплины!"*

— Гаспод (готов следить за режимом)"""
            
            gaspode_registered = gaspode_greeting + time_instruction
        else:
            # Fallback на старое сообщение
            gender_display = "мужчина" if gender == "male" else "женщина"
            gender_pronoun = "гражданин" if gender == "male" else "гражданка"
            
            gaspode_registered = f"""
🐺 **Отлично, {gender_pronoun} {user.first_name}!**

Гаспод записал: {gender_display}. Теперь все данные в протоколе Стражи.

**Программа исправления "Табекс" активирована!**

📝 **А теперь введи время первой таблетки:**
Когда ты сегодня принял первую таблетку Табекса?
Формат: **ЧЧ:ММ** (например: 08:30 или 14:15)

*"Закон - он как табак. Бросить тяжело, но надо."*

— Гаспод (записал всё в протокол)
"""
        
        await query.edit_message_text(gaspode_registered, parse_mode='Markdown')
        
        # Устанавливаем состояние ожидания времени
        context.user_data['awaiting_first_dose_time'] = True
        context.user_data['user_obj'] = created_user
        context.user_data['course_obj'] = created_course
        
        logger.info(f"Создан пользователь {created_user} с гендером {gender} и курс лечения")
        
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя и курса: {e}")
        await query.edit_message_text(
            "🐺 Рррр! Что-то пошло не так с регистрацией в протоколе Стражи! "
            "Попробуй команду /start еще раз."
        )


def setup_callback_handlers(app: Application) -> None:
    """
    Регистрация всех обработчиков callback-запросов в приложении.
    
    Args:
        app: Экземпляр Telegram Application для регистрации handlers
    """
    try:
        # Универсальный обработчик всех callback-запросов
        app.add_handler(CallbackQueryHandler(button_callback))
        
        logger.info("Обработчики callback-запросов успешно зарегистрированы")
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчиков callback: {e}")
        raise
