"""
Обработчики команд Telegram-бота для системы напоминаний о Табексе.

Содержит все команды, доступные пользователям для взаимодействия с ботом.
"""
import logging
import re
from datetime import datetime, timedelta, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from core.models.user import User
from core.models.treatment import TreatmentCourse
from core.services.reminder_service import reminder_service
from core.services.character_service import character_service
from core.services.schedule_service import schedule_service
from database.repositories import UserRepository, TreatmentRepository, TabexRepository
from database.connection import init_database

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start - арест и допрос у Гаспода.
    
    Гаспод арестовывает курильщика и предлагает программу исправления.
    """
    user = update.effective_user
    user_repo = UserRepository()
    
    try:
        # Инициализируем базу данных, если нужно
        await init_database()
        
        # Очищаем флаги ожидания подтверждения удаления (отмена /quit)
        context.user_data.pop('awaiting_deletion_confirmation', None)
        context.user_data.pop('user_to_delete', None)
        
        # Проверяем, существует ли пользователь
        existing_user = await user_repo.get_by_telegram_id(user.id)
        
        if existing_user:
            # Пользователь уже зарегистрирован, проверяем активный курс
            treatment_repo = TreatmentRepository()
            active_course = await treatment_repo.get_active_by_user_id(existing_user.user_id)
            
            if active_course:
                gaspode_return = f"""
🐺 **Рррр! Опять ты, {existing_user.first_name}!**

Гаспод помнит всех нарушителей. У тебя уже есть активная программа исправления!

**Текущий статус:**
• День лечения: {active_course.days_since_start}
• Фаза: {active_course.current_phase}  
• Персонаж: {active_course.current_character}

Не пытайся сбежать! Используй /stats для проверки прогресса.

*"Второй раз попался - значит, не научился с первого раза."*
"""
                await update.message.reply_text(gaspode_return, parse_mode='Markdown')
                return
            else:
                # Пользователь есть, но нет активного курса - начинаем новый
                await _start_new_course_for_existing_user(update, existing_user)
                return
        
        # Новый пользователь - показываем выбор гендера
        gaspode_arrest = f"""
🐺 **РРРР! Попался, гражданин {user.first_name}!**

Гаспод, дежурный пёс Городской Стражи Анк-Морпорка. Тебя арестовали по подозрению в курении табака в общественном месте!

Но у тебя есть выбор: тюрьма или программа исправления "Табекс" под надзором стражи. 

**Что скажешь?** *(Ясное дело, выберешь программу - все выбирают)*

Но сначала, для протокола, укажи свой пол. Это важно для... эээ... *"персонального подхода"* в исправлении.

*"Закон должен знать, с кем имеет дело."*

— Гаспод (арестовавший очередного курильщика)
"""
        
        # Создаем inline-клавиатуру для выбора гендера
        keyboard = [
            [InlineKeyboardButton("👨 Мужчина", callback_data=f"gender_male_{user.id}")],
            [InlineKeyboardButton("👩 Женщина", callback_data=f"gender_female_{user.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            gaspode_arrest,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        logger.info(f"Гаспод арестовал нового пользователя {user.id} ({user.first_name})")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}")
        await update.message.reply_text(
            "🐺 Рррр! Что-то пошло не так с арестом! "
            "Попробуй еще раз или беги, пока Гаспод не разозлился."
        )


async def _start_new_course_for_existing_user(update: Update, user_obj: User) -> None:
    """
    Начинает новый курс лечения для существующего пользователя.
    
    Args:
        update: Объект обновления Telegram
        user_obj: Объект пользователя из базы данных
    """
    try:
        # Создаем новый курс лечения
        treatment_repo = TreatmentRepository()
        
        new_course = TreatmentCourse(
            course_id=None,
            user_id=user_obj.user_id,
            start_date=date.today(),
            current_phase=1,
            current_character='gaspode'
        )
        
        created_course = await treatment_repo.create(new_course)
        
        gaspode_new_course = f"""
🐺 **Ррр, опять за старое, {user_obj.first_name}?**

Ладно, Гаспод не откажет в повторном шансе. Все курят, все хотят бросить.

**Новый курс лечения "Табекс" начинается!**

Теперь введи время, когда ты сегодня принял первую таблетку. 
Формат: **ЧЧ:ММ** (например: 08:30 или 14:15)

*"Сколько волка ни корми, а он все равно в лес смотрит. Но с Табексом может получиться."*

— Гаспод (готов следить снова)
"""
        
        await update.message.reply_text(gaspode_new_course, parse_mode='Markdown')
        
        logger.info(f"Создан новый курс лечения {created_course} для существующего пользователя {user_obj}")
        
    except Exception as e:
        logger.error(f"Ошибка создания нового курса для пользователя {user_obj.user_id}: {e}")
        await update.message.reply_text(
            "🐺 Рррр! Что-то пошло не так с новым курсом! "
            "Попробуй /start еще раз или беги к ветеринару!"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /help - краткая справка от Гаспода.
    """
    user = update.effective_user
    
    gaspode_help = """
🐺 **Инструкции от Гаспода**

Слушай внимательно, двуногий. Гаспод объясняет только один раз.

**Доступные команды:**
/start - арест и начало программы исправления (встреча с Гаспода)
/stats - посмотреть свой прогресс в исправлении
/quit - полное удаление из системы (требует подтверждения)
/help - эта справка (ты уже тут)

**Как это работает:**
1. Говоришь /start - Гаспод тебя арестовывает
2. Выбираешь свой пол (важно для протокола)
3. Вводишь время первой таблетки  
4. Получаешь напоминания от разных стражников по расписанию фаз
5. Принимаешь таблетку через inline-кнопки
6. Смотришь /stats для контроля прогресса

**Кнопки в напоминаниях:**
• ✅ ТАБЛЕТКА ПРИНЯТА - подтверждение приёма
• ⏰ ОТЛОЖИТЬ НА 5 МИН - отсрочка напоминания  
• ❌ ПРОПУСК - намеренный пропуск дозы

По мере прохождения курса тебя будут передавать разным персонажам Стражи. 25 дней до финала!

*"Закон как кость - грызть долго, но полезно для зубов."*

— Гаспод, Городская Стража (дежурный пёс)
"""
    
    try:
        await update.message.reply_text(
            gaspode_help,
            parse_mode='Markdown'
        )
        logger.info(f"Гаспод дал инструкции пользователю {user.id} ({user.first_name})")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке справки: {e}")
        await update.message.reply_text(
            "🐺 Рррр! Что-то пошло не так с инструкциями! "
            "Попробуй позже или беги к ветеринару."
        )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик неизвестных команд.
    
    Отвечает пользователю, если он ввёл неизвестную команду.
    """
    user = update.effective_user
    command = update.message.text
    
    vimes_unknown = f"""
🏴‍☠️ **Что за ерунда, гражданин?**

Команда `{command}` не входит в мои полномочия. 

Капитан Ваймс понимает только:
• /start - встретиться со Стражей
• /stats - проверить свой прогресс
• /help - получить инструкции

Остальное - не мое дело. У Стражи есть более важные вопросы, чем твои фантазии.

*"Если не знаешь, что делать, делай то, что знаешь."*
"""
    
    try:
        await update.message.reply_text(
            vimes_unknown,
            parse_mode='Markdown'
        )
        logger.info(f"Капитан Ваймс не понял команду '{command}' от пользователя {user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке неизвестной команды: {e}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /stats - статистика прогресса от текущего персонажа.
    """
    user = update.effective_user
    
    try:
        await init_database()
        
        # Получаем данные пользователя и курса
        user_repo = UserRepository()
        user_obj = await user_repo.get_by_telegram_id(user.id)
        
        if not user_obj:
            await update.message.reply_text(
                "❓ Ты не зарегистрирован в системе. Начни с команды /start"
            )
            return
        
        treatment_repo = TreatmentRepository()
        active_course = await treatment_repo.get_active_by_user_id(user_obj.user_id)
        
        if not active_course:
            await update.message.reply_text(
                "❓ У тебя нет активного курса лечения. Начни новый с команды /start"
            )
            return
        
        # Получаем текущего персонажа
        current_character = character_service.get_current_character(active_course)
        
        # Получаем статистику из базы данных
        tabex_repo = TabexRepository()
        all_logs = await tabex_repo.get_logs_by_course_id(active_course.course_id)
        
        # Вычисляем статистику
        total_scheduled = len(all_logs)
        taken_count = sum(1 for log in all_logs if log.is_taken)
        missed_count = sum(1 for log in all_logs if log.is_missed or log.is_skipped)
        
        compliance_percent = int((taken_count / max(total_scheduled, 1)) * 100)
        days_passed = active_course.days_since_start
        
        # Определяем, бросил ли курить (5-й день прошел)
        quit_smoking_info = ""
        if days_passed >= 5:
            quit_date = active_course.smoking_quit_date or (active_course.start_date + timedelta(days=4))
            days_smoke_free = (date.today() - quit_date).days + 1
            quit_smoking_info = f"🚭 **Дни без курения:** {days_smoke_free}\n"
        
        # Генерируем отчет от персонажа
        stats_message = f"""
{current_character.emoji} **Отчет {current_character.name} о твоем прогрессе**

📊 **Статистика программы исправления:**

📅 **Дата начала:** {active_course.start_date.strftime('%d.%m.%Y')}
⏰ **Дней прошло:** {days_passed}/25
📊 **Текущая фаза:** {active_course.current_phase}
{quit_smoking_info}
✅ **Принято таблеток:** {taken_count}
❌ **Пропущено:** {missed_count}
📈 **Соблюдение режима:** {compliance_percent}%

**Текущий персонаж:** {current_character.name} {current_character.emoji}

*{current_character.get_encouragement_message(user_obj.first_name, user_obj.gender, compliance_percent)}*
"""
        
        await update.message.reply_text(
            stats_message,
            parse_mode='Markdown'
        )
        logger.info(f"{current_character.name} показал статистику пользователю {user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке статистики: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при получении статистики. "
            "Попробуйте позже или обратитесь к администратору."
        )


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик текстовых сообщений от пользователей.
    
    Обрабатывает:
    - Подтверждение удаления "ПОДТВЕРЖДАЮ"
    - Ввод времени первого приёма таблетки
    """
    user = update.effective_user
    text = update.message.text.strip()
    
    # Проверяем подтверждение удаления
    if context.user_data.get('awaiting_deletion_confirmation'):
        if text == "ПОДТВЕРЖДАЮ":
            await handle_deletion_confirmation(update, context)
            return
        else:
            await update.message.reply_text(
                "❓ Для подтверждения удаления напиши точно: **ПОДТВЕРЖДАЮ**\n"
                "Для отмены используй: `/start`",
                parse_mode='Markdown'
            )
            return
    
    # Проверяем, ожидаем ли мы ввод времени от этого пользователя
    if not context.user_data.get('awaiting_first_dose_time'):
        return  # Это не ввод времени, игнорируем
    
    # Паттерн для времени в формате ЧЧ:ММ
    time_pattern = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$'
    match = re.match(time_pattern, text)
    
    if not match:
        gaspode_error = """
🐺 **Ррр, что за собачья чушь?**

Гаспод ясно сказал: формат **ЧЧ:ММ**

Примеры правильного ввода:
• 08:30
• 14:15  
• 09:00
• 21:45

Попробуй еще раз. Собачье терпение не безгранично.

*"Даже собаки понимают время лучше некоторых людей."*
"""
        await update.message.reply_text(gaspode_error, parse_mode='Markdown')
        return
    
    try:
        # Время корректное, обрабатываем
        hours, minutes = int(match.group(1)), int(match.group(2))
        first_dose_time = f"{hours:02d}:{minutes:02d}"
        
        # Получаем данные пользователя и курса из context
        user_obj = context.user_data.get('user_obj')
        course_obj = context.user_data.get('course_obj')
        
        if not user_obj:
            # Если нет данных пользователя в контексте, попробуем получить из БД
            user_repo = UserRepository()
            user_obj = await user_repo.get_by_telegram_id(user.id)
            
            if not user_obj:
                await update.message.reply_text(
                    "🐺 Рррр! Гаспод тебя не помнит! Начни с команды /start"
                )
                return
        
        if not course_obj:
            # Если нет данных курса, получаем активный курс из БД
            treatment_repo = TreatmentRepository()
            course_obj = await treatment_repo.get_active_by_user_id(user_obj.user_id)
            
            if not course_obj:
                await update.message.reply_text(
                    "🐺 Рррр! У тебя нет активного курса лечения! Начни с команды /start"
                )
                return
        
        # Сохраняем время в пользовательских данных
        context.user_data['first_dose_time'] = first_dose_time
        context.user_data['awaiting_first_dose_time'] = False
        context.user_data['program_started'] = True
        
        # Получаем текущего персонажа (должен быть Гаспод)
        current_character = character_service.get_current_character(course_obj)
        
        # Создаем запись о принятой первой дозе
        from core.models.tabex_log import TabexLog, TabexLogStatus
        from database.repositories import TabexRepository
        
        tabex_repo = TabexRepository()
        now = datetime.now()
        first_time = datetime.combine(now.date(), datetime.strptime(first_dose_time, "%H:%M").time())
        
        # Создаем запись о первой дозе как принятой
        first_dose_log = TabexLog(
            log_id=None,
            course_id=course_obj.course_id,
            scheduled_time=first_time,
            actual_time=first_time,
            status=TabexLogStatus.TAKEN.value,
            phase=course_obj.current_phase,
            character_response=f"{current_character.name} записал первый приём в {first_dose_time}"
        )
        await tabex_repo.create_log(first_dose_log)
        logger.info(f"Создана запись о первой дозе в {first_dose_time} для пользователя {user_obj.telegram_id}")
        
        if first_time < now:
            # Время уже прошло сегодня - ищем пропущенные дозы
            existing_logs = [first_dose_log]  # Включаем созданную первую дозу
            overdue_doses = schedule_service.get_overdue_doses(course_obj, first_dose_time, existing_logs)
            
            if overdue_doses:
                # Есть пропущенные дозы - начинаем интерактивный опрос
                await _start_interactive_catchup(update, context, user_obj, course_obj, current_character, overdue_doses, first_dose_time)
                return
        
        # Нет пропущенных доз - запускаем обычный режим
        await _start_normal_program(update, context, user_obj, course_obj, current_character, first_dose_time)
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении времени: {e}")
        await update.message.reply_text(
            "🐺 Рррр! Что-то пошло не так с записью времени! "
            "Попробуй /start еще раз или беги к ветеринару!"
        )


async def _start_interactive_catchup(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   user_obj: User, course_obj: TreatmentCourse,
                                   current_character, overdue_doses, first_dose_time: str) -> None:
    """
    Запускает интерактивный опрос по пропущенным дозам.
    
    Args:
        update: Объект обновления Telegram
        context: Контекст обработчика
        user_obj: Объект пользователя
        course_obj: Объект курса лечения
        current_character: Текущий персонаж
        overdue_doses: Список пропущенных доз
        first_dose_time: Время первой дозы
    """
    try:
        gender_pronoun = "гражданин" if user_obj.is_male() else "гражданка"
        
        # Сохраняем состояние для callback'ов
        context.user_data['catchup_mode'] = True
        context.user_data['overdue_doses'] = overdue_doses
        context.user_data['current_catchup_index'] = 0
        context.user_data['first_dose_time'] = first_dose_time
        
        # Сообщение о начале опроса
        intro_message = f"""
{current_character.emoji} **Стоп, {gender_pronoun} {user_obj.first_name}!**

{current_character.name} заметил: с **{first_dose_time}** уже прошло время для **{len(overdue_doses)} доз**!

Нужно выяснить - что ты делал{"" if user_obj.gender == "male" else "а"} всё это время.

**Сейчас проведём допрос по каждой пропущенной дозе.**

*"Стража должна знать правду. Всю правду."*

— {current_character.name} (начинает расследование)
"""
        
        await update.message.reply_text(
            intro_message,
            parse_mode='Markdown'
        )
        
        # Запускаем опрос по первой дозе
        await _ask_about_dose(update, context, user_obj, overdue_doses[0], 0, len(overdue_doses), current_character)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске интерактивного опроса: {e}")
        await update.message.reply_text(
            "🐺 Рррр! Что-то пошло не так с опросом! "
            "Попробуй /start еще раз или беги к ветеринару!"
        )


async def _ask_about_dose(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         user_obj: User, dose_schedule, dose_index: int, total_doses: int,
                         current_character) -> None:
    """
    Задает вопрос о конкретной пропущенной дозе.
    
    Args:
        update: Объект обновления
        context: Контекст обработчика
        user_obj: Объект пользователя
        dose_schedule: Расписание дозы
        dose_index: Индекс текущей дозы
        total_doses: Общее количество доз
        current_character: Текущий персонаж
    """
    try:
        gender_pronoun = "гражданин" if user_obj.is_male() else "гражданка"
        dose_time = dose_schedule.scheduled_time.strftime("%H:%M")
        
        # Определяем, это последняя (самая актуальная) доза или нет
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
        
        await update.message.reply_text(
            question_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка при задании вопроса о дозе: {e}")


async def _start_normal_program(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               user_obj: User, course_obj: TreatmentCourse, 
                               current_character, first_dose_time: str) -> None:
    """
    Запускает обычный режим программы без пропущенных доз.
    
    Args:
        update: Объект обновления
        context: Контекст обработчика  
        user_obj: Объект пользователя
        course_obj: Объект курса лечения
        current_character: Текущий персонаж
        first_dose_time: Время первой дозы
    """
    try:
        gender_pronoun = "гражданин" if user_obj.is_male() else "гражданка"
        
        gaspode_confirmation = f"""
{current_character.emoji} **Отлично, {gender_pronoun} {user_obj.first_name}!**

{current_character.name} записал: первый приём в **{first_dose_time}**.

**Программа исправления активирована!** ✅

Теперь Городская Стража будет наведываться к тебе для проверки соблюдения режима по расписанию фаз лечения.

*"Регулярность — это основа дисциплины. А дисциплина — основа успеха."*

— {current_character.name} (теперь официально следит за твоим исправлением)

**Используй /stats для контроля прогресса.**
"""
        
        await update.message.reply_text(
            gaspode_confirmation, 
            parse_mode='Markdown'
        )
        logger.info(f"Пользователь {user_obj.telegram_id} установил время первого приёма: {first_dose_time}")
        
        # Запускаем систему напоминаний
        success = await reminder_service.start_reminders_for_user(user_obj.telegram_id, first_dose_time, context.bot)
        if success:
            logger.info(f"Напоминания успешно запущены для пользователя {user_obj.telegram_id}")
        else:
            logger.error(f"Ошибка запуска напоминаний для пользователя {user_obj.telegram_id}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при запуске напоминаний. Попробуйте перезапустить команду /start."
            )
            
    except Exception as e:
        logger.error(f"Ошибка при запуске обычной программы: {e}")


async def handle_deletion_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает подтверждение удаления пользователя.
    
    Выполняет полное удаление всех данных пользователя из системы.
    """
    user = update.effective_user
    user_id_to_delete = context.user_data.get('user_to_delete')
    
    try:
        if not user_id_to_delete:
            await update.message.reply_text(
                "⚠️ Ошибка: не найден ID пользователя для удаления. Попробуй /quit заново."
            )
            return
        
        # Получаем все репозитории
        user_repo = UserRepository()
        treatment_repo = TreatmentRepository()
        tabex_repo = TabexRepository()
        
        # Останавливаем напоминания
        await reminder_service.stop_reminders_for_user(user.id)
        
        # Удаляем данные в правильном порядке (от зависимых к независимым)
        # 1. Удаляем записи приёмов и взаимодействия (зависят от курсов)
        await tabex_repo.delete_all_logs_for_user(user_id_to_delete)
        await tabex_repo.delete_all_interactions_for_user(user_id_to_delete)
        
        # 2. Удаляем курсы лечения (зависят от пользователя)
        await treatment_repo.delete_all_by_user_id(user_id_to_delete)
        
        # 3. Удаляем самого пользователя
        await user_repo.delete(user_id_to_delete)
        
        # Очищаем данные контекста
        context.user_data.clear()
        
        death_farewell = """
💀 **ГОТОВО.**

Смерть выполнила твою просьбу. Твоё досье стёрто из архивов Стражи.

**Что произошло:**
✅ Удалены все курсы лечения
✅ Удалена вся статистика
✅ Удалена история взаимодействий  
✅ Остановлены все напоминания
✅ Стёрта твоя учётная запись

Теперь ты можешь начать заново. Используй `/start` когда будешь готов к новой программе исправления.

*"Некоторые люди думают, что Смерть жестока. Но на самом деле Смерть даёт второй шанс."*

— Смерть (архивариус забвения)

**Увидимся снова, когда решишь вернуться...**
"""
        
        await update.message.reply_text(
            death_farewell,
            parse_mode='Markdown'
        )
        
        logger.info(f"Пользователь {user.id} полностью удален из системы")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя {user.id}: {e}")
        await update.message.reply_text(
            "💀 **ОШИБКА СМЕРТИ**\n\n"
            "Что-то пошло не так при стирании досье. "
            "Попробуй позже или обратись к администратору."
        )
        # Очищаем флаг ожидания даже при ошибке
        context.user_data.pop('awaiting_deletion_confirmation', None)
        context.user_data.pop('user_to_delete', None)


async def quit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /quit - полное удаление пользователя из системы.
    
    Запрашивает подтверждение и удаляет ВСЕ данные пользователя.
    """
    user = update.effective_user
    
    try:
        await init_database()
        
        # Получаем данные пользователя
        user_repo = UserRepository()
        user_obj = await user_repo.get_by_telegram_id(user.id)
        
        if not user_obj:
            await update.message.reply_text(
                "❓ Ты не зарегистрирован в системе. Нечего удалять."
            )
            return
        
        # Проверяем, не ждем ли мы уже подтверждение от этого пользователя
        if context.user_data.get('awaiting_deletion_confirmation'):
            await update.message.reply_text(
                "⚠️ Я уже жду твоего подтверждения. Напиши **ПОДТВЕРЖДАЮ** или /start чтобы отменить.",
                parse_mode='Markdown'
            )
            return
        
        # Устанавливаем флаг ожидания подтверждения
        context.user_data['awaiting_deletion_confirmation'] = True
        context.user_data['user_to_delete'] = user_obj.user_id
        
        warning_message = f"""
💀 **ВНИМАНИЕ, {user_obj.first_name}!**

Ты запросил полное удаление из системы Табекс-помощника.

**Это действие:**
• Удалит ВСЕ твои данные из системы
• Удалит всю историю лечения  
• Удалит все курсы и статистику
• Остановит все напоминания
• **ДЕЙСТВИЕ НЕОБРАТИМО!**

После удаления ты сможешь начать заново с чистого листа.

**Для подтверждения напиши точно:** `ПОДТВЕРЖДАЮ`
**Для отмены используй:** `/start`

*"Смерть - это не конец. Это просто... очень неудобно."*

— Смерть (готов стереть твоё досье)
"""
        
        await update.message.reply_text(
            warning_message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Пользователь {user.id} запросил удаление данных, ждем подтверждения")
        
    except Exception as e:
        logger.error(f"Ошибка при инициации удаления пользователя: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте позже или обратитесь к администратору."
        )


def setup_command_handlers(app: Application) -> None:
    """
    Регистрация всех обработчиков команд в приложении.
    
    Args:
        app: Экземпляр Telegram Application для регистрации handlers
    """
    try:
        # MVP команды от капитана Ваймса
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("stats", stats_command))
        
        # Команда завершения курса досрочно
        app.add_handler(CommandHandler("quit", quit_command))
        
        # Обработчик текстовых сообщений (время, подтверждение удаления)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
        
        logger.info("Обработчики команд успешно зарегистрированы")
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчиков команд: {e}")
        raise
