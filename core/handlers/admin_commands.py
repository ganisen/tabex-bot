"""
Административные команды для тестирования системы Табекс-бота.

Позволяют быстро тестировать прохождение всего курса лечения,
проверять смену персонажей, гендерные различия и критические сценарии.
"""
import logging
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.models.treatment import TreatmentCourse, TreatmentStatus
from core.models.user import User
from core.services.character_service import character_service
from core.services.schedule_service import schedule_service
from core.services.reminder_service import reminder_service
from database.repositories import UserRepository, TreatmentRepository, TabexRepository
from config.tabex_phases import phase_manager, TABEX_PHASES_CONFIG

logger = logging.getLogger(__name__)

# ID админа - замените на свой Telegram ID
ADMIN_ID = 5700485536  # Заменить на ваш Telegram ID

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user_id == ADMIN_ID


async def admin_jump_day_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Админская команда для быстрого перехода на любой день курса.
    
    Использование: /admin_jump_day 15
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Доступ запрещен. Эта команда только для администратора.")
        return
    
    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                "📋 **Использование:** `/admin_jump_day <день>`\n\n"
                "Пример: `/admin_jump_day 15`\n"
                "Доступные дни: 1-25",
                parse_mode='Markdown'
            )
            return
        
        target_day = int(args[0])
        if not 1 <= target_day <= 25:
            await update.message.reply_text("❌ День должен быть от 1 до 25")
            return
        
        # Получаем данные пользователя и курса
        user_repo = UserRepository()
        treatment_repo = TreatmentRepository()
        
        user_obj = await user_repo.get_by_telegram_id(user.id)
        if not user_obj:
            await update.message.reply_text("❌ Пользователь не найден. Запустите /start")
            return
        
        course = await treatment_repo.get_active_by_user_id(user_obj.user_id)
        if not course:
            await update.message.reply_text("❌ Активный курс не найден. Запустите /start")
            return
        
        # Рассчитываем новую дату начала
        new_start_date = date.today() - timedelta(days=target_day - 1)
        
        # Обновляем курс
        course.start_date = new_start_date
        
        # Определяем новую фазу и персонажа
        phase_config = phase_manager.get_phase_for_day(target_day)
        if phase_config:
            course.current_phase = phase_config.phase_number
            course.current_character = phase_config.character
        
        await treatment_repo.update(course)
        
        # Получаем информацию о персонаже
        current_character = character_service.get_current_character(course)
        
        # Специальное событие для 5-го дня
        special_info = ""
        if target_day == 5:
            if not course.smoking_quit_date:
                course.smoking_quit_date = new_start_date + timedelta(days=4)
                await treatment_repo.update(course)
            special_info = "\n🚭 **КРИТИЧЕСКИЙ ДЕНЬ: полный отказ от курения!**"
        
        result_message = f"""
🔧 **АДМИН: Переход на день {target_day}**

✅ **Обновлен курс пользователя {user_obj.first_name}**

📅 **Новая дата начала:** {new_start_date.strftime('%d.%m.%Y')}
📊 **Текущий день:** {target_day}/25
🎭 **Фаза:** {course.current_phase}
👤 **Персонаж:** {current_character.name} {current_character.emoji}
{special_info}

*"Время - это иллюзия. Обеденное время - тем более."*

— Админ Времени (манипулирует реальностью)
"""
        
        await update.message.reply_text(result_message, parse_mode='Markdown')
        logger.info(f"Админ перевел пользователя {user.id} на день {target_day}")
        
    except ValueError:
        await update.message.reply_text("❌ Неправильный формат дня. Используйте число от 1 до 25")
    except Exception as e:
        logger.error(f"Ошибка в admin_jump_day: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")


async def admin_set_phase_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Админская команда для принудительного изменения фазы и персонажа.
    
    Использование: /admin_set_phase 3
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Доступ запрещен. Эта команда только для администратора.")
        return
    
    try:
        args = context.args
        if not args:
            phase_list = phase_manager.get_phase_summary()
            phases_text = "\n".join([f"**{num}**: {desc}" for num, desc in phase_list.items()])
            
            await update.message.reply_text(
                f"📋 **Использование:** `/admin_set_phase <номер_фазы>`\n\n"
                f"**Доступные фазы:**\n{phases_text}\n\n"
                f"Пример: `/admin_set_phase 3`",
                parse_mode='Markdown'
            )
            return
        
        target_phase = int(args[0])
        if target_phase not in TABEX_PHASES_CONFIG:
            await update.message.reply_text("❌ Фаза должна быть от 1 до 5")
            return
        
        # Получаем данные пользователя и курса
        user_repo = UserRepository()
        treatment_repo = TreatmentRepository()
        
        user_obj = await user_repo.get_by_telegram_id(user.id)
        if not user_obj:
            await update.message.reply_text("❌ Пользователь не найден. Запустите /start")
            return
        
        course = await treatment_repo.get_active_by_user_id(user_obj.user_id)
        if not course:
            await update.message.reply_text("❌ Активный курс не найден. Запустите /start")
            return
        
        # Обновляем фазу и персонажа
        phase_config = TABEX_PHASES_CONFIG[target_phase]
        course.current_phase = target_phase
        course.current_character = phase_config.character
        
        await treatment_repo.update(course)
        
        # Получаем информацию о персонаже
        current_character = character_service.get_current_character(course)
        
        result_message = f"""
🔧 **АДМИН: Смена фазы**

✅ **Обновлен курс пользователя {user_obj.first_name}**

🎭 **Новая фаза:** {target_phase}
👤 **Новый персонаж:** {current_character.name} {current_character.emoji}
⏰ **Интервал приема:** каждые {phase_config.interval_hours}ч
💊 **Таблеток в день:** {phase_config.doses_per_day}
📖 **Описание:** {phase_config.description}

*"Иногда нужно заставить время подчиниться."*

— Админ Фаз (управляет переходами)
"""
        
        await update.message.reply_text(result_message, parse_mode='Markdown')
        logger.info(f"Админ установил фазу {target_phase} для пользователя {user.id}")
        
    except ValueError:
        await update.message.reply_text("❌ Неправильный формат фазы. Используйте число от 1 до 5")
    except Exception as e:
        logger.error(f"Ошибка в admin_set_phase: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")


async def admin_test_gender_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Админская команда для тестирования гендерно-зависимых текстов всех персонажей.
    
    Показывает, как каждый персонаж обращается к мужчинам и женщинам.
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Доступ запрещен. Эта команда только для администратора.")
        return
    
    try:
        # Получаем данные пользователя
        user_repo = UserRepository()
        user_obj = await user_repo.get_by_telegram_id(user.id)
        
        if not user_obj:
            await update.message.reply_text("❌ Пользователь не найден. Запустите /start")
            return
        
        # Создаем клавиатуру для выбора персонажа
        characters = [
            ("Гаспод", "gaspode", 1),
            ("Шнобби и Колон", "nobby_colon", 2),
            ("Ангва", "angua", 3),
            ("Моркоу", "carrot", 4),
            ("Ваймс", "vimes", 5),
            ("Витинари", "vetinari", 6),
            ("СМЕРТЬ", "death", 7)
        ]
        
        keyboard = []
        for name, char_id, num in characters:
            keyboard.append([InlineKeyboardButton(f"{num}. {name}", callback_data=f"test_gender_{char_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        test_info = f"""
🔧 **АДМИН: Тестирование гендерных текстов**

Выберите персонажа для тестирования гендерно-зависимых сообщений.

**Ваш текущий пол:** {'Мужской' if user_obj.is_male() else 'Женский'}

Для каждого персонажа будут показаны:
• Приветствие
• Напоминание о дозе
• Поощрение за прогресс
• Предупреждение при пропуске

*"Важно знать, как с тобой говорят."*

— Админ Гендеров (проверяет корректность)
"""
        
        await update.message.reply_text(
            test_info,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_test_gender: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")


async def admin_simulate_full_course_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Админская команда для автоматической симуляции полного курса лечения.
    
    Проводит курс от 1 до 25 дня с демонстрацией всех переходов.
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Доступ запрещен. Эта команда только для администратора.")
        return
    
    try:
        # Получаем данные пользователя и курса
        user_repo = UserRepository()
        treatment_repo = TreatmentRepository()
        
        user_obj = await user_repo.get_by_telegram_id(user.id)
        if not user_obj:
            await update.message.reply_text("❌ Пользователь не найден. Запустите /start")
            return
        
        course = await treatment_repo.get_active_by_user_id(user_obj.user_id)
        if not course:
            await update.message.reply_text("❌ Активный курс не найден. Запустите /start")
            return
        
        # Создаем клавиатуру для выбора режима симуляции
        keyboard = [
            [InlineKeyboardButton("🚀 Быстрая симуляция (ключевые дни)", callback_data="sim_fast")],
            [InlineKeyboardButton("📋 Полная симуляция (все 25 дней)", callback_data="sim_full")],
            [InlineKeyboardButton("🎭 Только переходы персонажей", callback_data="sim_characters")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        sim_info = f"""
🔧 **АДМИН: Симуляция полного курса**

Запуск автоматической симуляции курса лечения для **{user_obj.first_name}** ({'М' if user_obj.is_male() else 'Ж'}).

**Режимы симуляции:**

🚀 **Быстрая** — показывает дни 1, 5, 13, 17, 21, 25 (переходы + критический день)

📋 **Полная** — проходит все 25 дней с демонстрацией каждого перехода

🎭 **Персонажи** — показывает только смену персонажей без изменения курса

*"Время - это четвертое измерение. Но для админа - всего лишь переменная."*

— Админ Симулятор (повелитель времени)
"""
        
        await update.message.reply_text(
            sim_info,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_simulate_full_course: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")


async def admin_reset_course_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Админская команда для сброса курса к первому дню.
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Доступ запрещен. Эта команда только для администратора.")
        return
    
    try:
        # Получаем данные пользователя и курса
        user_repo = UserRepository()
        treatment_repo = TreatmentRepository()
        tabex_repo = TabexRepository()
        
        user_obj = await user_repo.get_by_telegram_id(user.id)
        if not user_obj:
            await update.message.reply_text("❌ Пользователь не найден. Запустите /start")
            return
        
        course = await treatment_repo.get_active_by_user_id(user_obj.user_id)
        if not course:
            await update.message.reply_text("❌ Активный курс не найден. Запустите /start")
            return
        
        # Сбрасываем курс к началу
        course.start_date = date.today()
        course.current_phase = 1
        course.current_character = 'gaspode'
        course.smoking_quit_date = None
        
        await treatment_repo.update(course)
        
        # Удаляем все логи приемов
        await tabex_repo.delete_all_logs_for_user(user_obj.user_id)
        
        # Останавливаем напоминания и перезапускаем
        await reminder_service.stop_reminders_for_user(user.id)
        
        result_message = f"""
🔧 **АДМИН: Сброс курса**

✅ **Курс пользователя {user_obj.first_name} сброшен к началу**

📅 **Дата начала:** {course.start_date.strftime('%d.%m.%Y')} (сегодня)
📊 **День:** 1/25
🎭 **Фаза:** 1 (Начальная)
👤 **Персонаж:** Гаспод 🐺
🗑️ **Удалены:** все записи приемов
⏰ **Напоминания:** остановлены

**Для возобновления введите время первого приема.**

*"Каждый заслуживает второй шанс. И третий. И четвертый..."*

— Админ Перезагрузчик (мастер новых начал)
"""
        
        await update.message.reply_text(result_message, parse_mode='Markdown')
        logger.info(f"Админ сбросил курс для пользователя {user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка в admin_reset_course: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")


async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Админская команда справки по всем административным командам.
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Доступ запрещен. Эта команда только для администратора.")
        return
    
    help_text = """
🔧 **АДМИНСКИЕ КОМАНДЫ ТАБЕКС-БОТА**

**Навигация по курсу:**
`/admin_jump_day <день>` — перейти на конкретный день (1-25)
`/admin_set_phase <фаза>` — установить конкретную фазу (1-5)
`/admin_reset_course` — сбросить курс к первому дню

**Тестирование:**
`/admin_test_gender` — проверить гендерные тексты всех персонажей
`/admin_simulate_course` — автоматическая симуляция курса
`/admin_help` — эта справка

**Примеры использования:**
• `/admin_jump_day 5` — переход на критический день
• `/admin_jump_day 25` — переход к финалу с Витинари
• `/admin_set_phase 3` — перевод в фазу Ангвы
• `/admin_test_gender` — проверка текстов для текущего пола

**Порядок полного тестирования:**
1. Создать тестового пользователя мужского пола (/start)
2. Проверить каждый переход: дни 1→4→13→17→21→25
3. Протестировать критический день 5
4. Сбросить курс и повторить для женского пола
5. Проверить систему напоминаний и inline-кнопки

*"С большой силой приходит большая ответственность. И большие возможности для тестирования."*

— Админ Главный (повелитель системы)
"""
    
    try:
        await update.message.reply_text(help_text, parse_mode='Markdown')
        logger.info(f"Админ {user.id} запросил справку по админским командам")
        
    except Exception as e:
        logger.error(f"Ошибка в admin_help: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
