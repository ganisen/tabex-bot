"""
Обработчики callback'ов для административных команд.

Обрабатывает нажатия на inline-кнопки в админских командах:
- Тестирование гендерных текстов
- Симуляция курса лечения
- Демонстрация переходов персонажей
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from core.models.treatment import TreatmentCourse, TreatmentStatus
from core.services.character_service import character_service
from database.repositories import UserRepository, TreatmentRepository
from config.tabex_phases import phase_manager, TABEX_PHASES_CONFIG
from .admin_commands import is_admin

logger = logging.getLogger(__name__)


async def handle_admin_gender_test_callback(query: CallbackQuery, character_id: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает callback для тестирования гендерных текстов персонажа.
    
    Args:
        query: Callback query от inline кнопки
        character_id: ID персонажа для тестирования
        context: Контекст обработчика
    """
    user = query.from_user
    
    if not is_admin(user.id):
        await query.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    try:
        await query.answer()  # Убираем загрузку с кнопки
        
        # Получаем данные пользователя
        user_repo = UserRepository()
        user_obj = await user_repo.get_by_telegram_id(user.id)
        
        if not user_obj:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        # Получаем персонажа
        character = character_service.get_character_by_name(character_id)
        if not character:
            await query.edit_message_text(f"❌ Персонаж {character_id} не найден")
            return
        
        # Тестируем тексты для обоих полов
        male_texts = _generate_gender_texts(character, user_obj.first_name, "male")
        female_texts = _generate_gender_texts(character, user_obj.first_name, "female")
        
        test_result = f"""
🔧 **ТЕСТ: {character.name} {character.emoji}**

👨 **Для мужчин:**
{male_texts}

👩 **Для женщин:**
{female_texts}

**Выводы:**
• Персонаж корректно адаптируется к полу
• Тексты различаются по стилю обращения
• Гендерные особенности учтены

*"Каждому своё обращение."*

— Админ Тестировщик (проверяет инклюзивность)
"""
        
        await query.edit_message_text(test_result, parse_mode='Markdown')
        logger.info(f"Админ протестировал гендерные тексты для персонажа {character_id}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_gender_test_callback: {e}")
        await query.edit_message_text(f"❌ Произошла ошибка: {str(e)}")


def _generate_gender_texts(character, first_name: str, gender: str) -> str:
    """
    Генерирует набор тестовых текстов персонажа для указанного пола.
    
    Args:
        character: Объект персонажа
        first_name: Имя пользователя
        gender: Пол ("male" или "female")
        
    Returns:
        Отформатированная строка с тестовыми текстами
    """
    try:
        # Приветствие
        greeting = character.get_greeting_message(first_name, gender)
        
        # Напоминание
        reminder = character.get_reminder_message(first_name, gender, 3, 5)
        
        # Поощрение
        encouragement = character.get_encouragement_message(first_name, gender, 85)
        
        # Предупреждение
        warning = character.get_warning_message(first_name, gender, 2)
        
        return f"""
**Приветствие:**
_{greeting[:100]}..._

**Напоминание:**
_{reminder[:100]}..._

**Поощрение:**
_{encouragement[:100]}..._

**Предупреждение:**
_{warning[:100]}..._"""
        
    except Exception as e:
        return f"❌ Ошибка генерации текстов: {str(e)[:50]}..."


async def handle_admin_simulation_callback(query: CallbackQuery, sim_type: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает callback для симуляции курса лечения.
    
    Args:
        query: Callback query от inline кнопки
        sim_type: Тип симуляции (fast/full/characters)
        context: Контекст обработчика
    """
    user = query.from_user
    
    if not is_admin(user.id):
        await query.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    try:
        await query.answer()
        
        # Получаем данные пользователя и курса
        user_repo = UserRepository()
        treatment_repo = TreatmentRepository()
        
        user_obj = await user_repo.get_by_telegram_id(user.id)
        if not user_obj:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        course = await treatment_repo.get_active_by_user_id(user_obj.user_id)
        if not course:
            await query.edit_message_text("❌ Активный курс не найден")
            return
        
        # Определяем дни для симуляции
        if sim_type == "fast":
            days_to_simulate = [1, 5, 13, 17, 21, 25]
            title = "🚀 **БЫСТРАЯ СИМУЛЯЦИЯ**"
        elif sim_type == "full":
            days_to_simulate = list(range(1, 26))
            title = "📋 **ПОЛНАЯ СИМУЛЯЦИЯ**"
        else:  # characters
            days_to_simulate = [1, 4, 13, 17, 21, 26]  # 26 для Витинари
            title = "🎭 **СИМУЛЯЦИЯ ПЕРСОНАЖЕЙ**"
        
        # Начинаем симуляцию
        await query.edit_message_text(
            f"{title}\n\nЗапуск симуляции для **{user_obj.first_name}**...\n\n"
            f"⏳ Обрабатывается {len(days_to_simulate)} дней курса...",
            parse_mode='Markdown'
        )
        
        # Небольшая задержка для показа
        await asyncio.sleep(1)
        
        # Выполняем симуляцию
        results = await _simulate_course_days(user_obj, course, days_to_simulate, treatment_repo)
        
        # Отправляем результаты
        final_message = f"{title}\n\n{results}\n\n*Симуляция завершена успешно!*"
        
        await context.bot.send_message(
            chat_id=user.id,
            text=final_message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Админ выполнил симуляцию типа {sim_type}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_simulation_callback: {e}")
        await query.edit_message_text(f"❌ Произошла ошибка симуляции: {str(e)}")


async def _simulate_course_days(user_obj, course: TreatmentCourse, days_to_simulate: list, 
                              treatment_repo: TreatmentRepository) -> str:
    """
    Симулирует прохождение указанных дней курса.
    
    Args:
        user_obj: Объект пользователя
        course: Курс лечения
        days_to_simulate: Список дней для симуляции
        treatment_repo: Репозиторий курсов лечения
        
    Returns:
        Отформатированная строка с результатами симуляции
    """
    results = []
    original_start_date = course.start_date
    
    try:
        for day in days_to_simulate:
            # Рассчитываем дату для этого дня
            target_date = date.today() - timedelta(days=day - 1)
            course.start_date = target_date
            
            # Определяем фазу и персонажа
            if day <= 25:
                phase_config = phase_manager.get_phase_for_day(day)
                if phase_config:
                    course.current_phase = phase_config.phase_number
                    course.current_character = phase_config.character
            else:
                # День 26 - финал с Витинари
                course.current_character = 'vetinari'
            
            # Получаем персонажа
            current_character = character_service.get_current_character(course)
            
            # Специальная обработка критического 5-го дня
            special_info = ""
            if day == 5:
                course.smoking_quit_date = target_date
                special_info = " 🚭 КРИТИЧЕСКИЙ ДЕНЬ!"
            
            # Генерируем сообщение от персонажа
            if day == 26:
                # Финальная аудиенция у Витинари
                character_message = current_character.get_farewell_message(
                    user_obj.first_name, user_obj.gender
                )
                results.append(
                    f"📅 **ФИНАЛ** — {current_character.name} {current_character.emoji}\n"
                    f"*{character_message[:150]}...*\n"
                )
            else:
                character_message = current_character.get_encouragement_message(
                    user_obj.first_name, user_obj.gender, 85
                )
                results.append(
                    f"📅 **День {day}** — {current_character.name} {current_character.emoji}{special_info}\n"
                    f"*{character_message[:120]}...*\n"
                )
            
            # Добавляем задержку между "днями"
            await asyncio.sleep(0.5)
        
        return "\n".join(results)
        
    finally:
        # Восстанавливаем исходную дату начала курса
        course.start_date = original_start_date
        await treatment_repo.update(course)


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Главный обработчик всех админских callback'ов.
    
    Распределяет callback'ы по соответствующим функциям обработки.
    """
    query = update.callback_query
    user = query.from_user
    
    if not is_admin(user.id):
        await query.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    try:
        callback_data = query.data
        
        if callback_data.startswith("test_gender_"):
            # Тестирование гендерных текстов персонажа
            character_id = callback_data.replace("test_gender_", "")
            await handle_admin_gender_test_callback(query, character_id, context)
            
        elif callback_data.startswith("sim_"):
            # Симуляция курса
            sim_type = callback_data.replace("sim_", "")
            await handle_admin_simulation_callback(query, sim_type, context)
            
        else:
            await query.answer("❓ Неизвестная админская команда", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_callback: {e}")
        await query.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)
