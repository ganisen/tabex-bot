"""
Обработчики команд Telegram-бота для системы напоминаний о Табексе.

Содержит все команды, доступные пользователям для взаимодействия с ботом.
"""
import logging
import re
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start - встреча с капитаном Ваймсом.
    
    Капитан Ваймс приветствует нового "подопечного" и начинает программу исправления.
    """
    user = update.effective_user
    
    vimes_welcome = f"""
🏴‍☠️ **Так-так-так, {user.first_name}...**

Капитан Сэмюэл Ваймс, Городская Стража Анк-Морпорка. Рад, что ты попал в руки Закона, а не в какие-нибудь другие руки. Хотя, честно говоря, руки у меня довольно грубые.

Итак, я слышал, у тебя проблемы с курением? Что ж, это не первый раз, когда Стража берется за дело исправления граждан. У нас есть *опыт* в таких делах.

🚬 ➜ 🚭

Видишь стрелку? Это направление движения. Никаких поворотов назад, никаких "а что если", никаких "может быть завтра". Только вперед.

**Программа исправления "Табекс":**
Каждые 2 часа к тебе будет наведываться стража для... *проверки*. Можешь считать это дружеским напоминанием. Или недружеским. Мне все равно.

📝 **А теперь слушай внимательно, гражданин:**
Введи время, когда ты сегодня принял первую таблетку Табекса. 

Формат: **ЧЧ:ММ** (например: 08:30 или 14:15)

*"Время - это не деньги. Время - это время. А деньги - это деньги. Но без времени у тебя не будет денег на то, чтобы их потратить."*

— Капитан Ваймс (в данный момент следит за твоим исправлением)
"""
    
    try:
        await update.message.reply_text(
            vimes_welcome,
            parse_mode='Markdown'
        )
        logger.info(f"Капитан Ваймс встретил пользователя {user.id} ({user.first_name})")
        
        # Устанавливаем состояние ожидания времени
        context.user_data['awaiting_first_dose_time'] = True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке приветствия: {e}")
        await update.message.reply_text(
            "Привет! Я Табекс-бот. К сожалению, произошла ошибка при загрузке приветствия. "
            "Используйте /help для получения информации о командах."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /help - краткая справка от капитана Ваймса.
    """
    user = update.effective_user
    
    vimes_help = """
🏴‍☠️ **Инструкции от капитана Ваймса**

Слушай внимательно, гражданин. У Стражи нет времени повторять дважды.

**Доступные команды:**
/start - начать программу исправления (встреча с капитаном)
/stats - посмотреть свой прогресс в деле отказа от курения  
/help - эта справка (ты уже тут)

**Как это работает:**
1. Говоришь /start
2. Вводишь время первой таблетки  
3. Каждые 2 часа получаешь напоминание от Стражи
4. Принимаешь таблетку и подтверждаешь
5. Смотришь /stats для контроля прогресса

Больше никаких кнопочек, менюшек и прочих излишеств. Простота - признак надежности.

*"Сложные вещи просты. Простые вещи сложны. А очень простые вещи почти невозможны."*

— Капитан Ваймс, Городская Стража
"""
    
    try:
        await update.message.reply_text(
            vimes_help,
            parse_mode='Markdown'
        )
        logger.info(f"Капитан Ваймс дал инструкции пользователю {user.id} ({user.first_name})")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке справки: {e}")
        await update.message.reply_text(
            "Извините, произошла ошибка при загрузке справки. "
            "Попробуйте позже или обратитесь к администратору."
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
        vimes_error = """
🏴‍☠️ **Гражданин, ты издеваешься?**

Я ясно сказал: формат **ЧЧ:ММ**

Примеры правильного ввода:
• 08:30
• 14:15  
• 09:00
• 21:45

Попробуй еще раз. И на этот раз внимательнее.

*"Детали — это не детали. Детали создают дизайн."*
"""
        await update.message.reply_text(vimes_error, parse_mode='Markdown')
        return
    
    # Время корректное, обрабатываем
    hours, minutes = int(match.group(1)), int(match.group(2))
    first_dose_time = f"{hours:02d}:{minutes:02d}"
    
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
    
    vimes_confirmation = f"""
🏴‍☠️ **Отлично, гражданин {user.first_name}!**

Записано: первый приём в **{first_dose_time}**.

**Программа исправления активирована.** ✅

Теперь Городская Стража будет наведываться к тебе каждые **2 часа** для проверки соблюдения режима.

⏰ **Следующее напоминание:** {next_dose.strftime("%H:%M")}

Не вздумай пропускать! У капитана Ваймса хорошая память, и он помнит всех нарушителей режима.

*"Регулярность — это вежливость королей. И капитанов стражи тоже."*

— Капитан Ваймс (теперь официально следит за твоим исправлением)

**Используй /stats для контроля прогресса.**
"""
    
    try:
        await update.message.reply_text(
            vimes_confirmation, 
            parse_mode='Markdown'
        )
        logger.info(f"Пользователь {user.id} установил время первого приёма: {first_dose_time}")
        
        # TODO: В следующих этапах здесь будет планирование напоминаний
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении времени: {e}")
        await update.message.reply_text(
            "Капитан Ваймс принял информацию, но что-то пошло не так с записью. "
            "Попробуй /start еще раз."
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
