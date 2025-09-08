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
from database.repositories import UserRepository, TreatmentRepository
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
/help - эта справка (ты уже тут)

**Как это работает:**
1. Говоришь /start - Гаспод тебя арестовывает
2. Выбираешь свой пол (важно для протокола)
3. Вводишь время первой таблетки  
4. Каждые 2 часа получаешь напоминания от разных стражников
5. Принимаешь таблетку и подтверждаешь
6. Смотришь /stats для контроля прогресса

По мере прохождения курса тебя будут передавать разным персонажам Стражи. От простых стражников до самого Лорда Витинари!

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
    Обработчик команды /stats - статистика прогресса от капитана Ваймса.
    """
    user = update.effective_user
    
    # TODO: В следующих этапах здесь будет реальная статистика из БД
    vimes_stats = """
🏴‍☠️ **Отчет капитана Ваймса о твоем прогрессе**

📊 **Статистика программы исправления:**

*Пока что база данных не подключена, гражданин. Но капитан Ваймс ведет записи в блокноте.*

**Что будет здесь:**
• Дата начала программы исправления
• Количество принятых таблеток
• Количество пропущенных приёмов
• Процент соблюдения режима
• Дни без сигарет (когда это наступит)

**Текущий статус:** Программа настройки ⚙️

*"Статистика похожа на купальник: показывает многое, но скрывает самое главное."*

— Капитан Ваймс (пока что ведет учёт вручную)

Возвращайся позже, когда система будет полностью готова к работе.
"""
    
    try:
        await update.message.reply_text(
            vimes_stats,
            parse_mode='Markdown'
        )
        logger.info(f"Капитан Ваймс показал статистику пользователю {user.id} ({user.first_name})")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке статистики: {e}")
        await update.message.reply_text(
            "Капитан Ваймс временно не может показать статистику. "
            "Его блокнот где-то потерялся в архивах Стражи."
        )


async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик ввода времени первого приёма таблетки.
    """
    user = update.effective_user
    text = update.message.text.strip()
    
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
        
        # Рассчитываем следующий приём (через 2 часа)
        now = datetime.now()
        first_time = datetime.combine(now.date(), datetime.strptime(first_dose_time, "%H:%M").time())
        if first_time < now:
            first_time += timedelta(days=1)  # Если время уже прошло, то на следующий день
        
        next_dose = first_time + timedelta(hours=2)
        
        # Генерируем гендерно-зависимое подтверждение от Гаспода
        gender_pronoun = "гражданин" if user_obj.is_male() else "гражданка"
        
        gaspode_confirmation = f"""
🐺 **Отлично, {gender_pronoun} {user_obj.first_name}!**

Гаспод записал: первый приём в **{first_dose_time}**.

**Программа исправления активирована!** ✅

Теперь Городская Стража будет наведываться к тебе каждые **2 часа** для проверки соблюдения режима.

⏰ **Следующее напоминание:** {next_dose.strftime("%H:%M")}

Не вздумай пропускать! Гаспод помнит всех нарушителей.

*"Регулярность — это основа дисциплины. А дисциплина — основа успеха."*

— Гаспод (теперь официально следит за твоим исправлением)

**Используй /stats для контроля прогресса.**
"""
        
        await update.message.reply_text(
            gaspode_confirmation, 
            parse_mode='Markdown'
        )
        logger.info(f"Пользователь {user.id} установил время первого приёма: {first_dose_time}")
        
        # TODO: В следующих этапах здесь будет планирование напоминаний и создание записей TabexLog
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении времени: {e}")
        await update.message.reply_text(
            "🐺 Рррр! Что-то пошло не так с записью времени! "
            "Попробуй /start еще раз или беги к ветеринару!"
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
        
        # Обработчик ввода времени (текстовые сообщения)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_input))
        
        logger.info("Обработчики команд капитана Ваймса успешно зарегистрированы")
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчиков команд: {e}")
        raise
