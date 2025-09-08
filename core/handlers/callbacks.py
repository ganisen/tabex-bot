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
        
        await treatment_repo.create(new_course)
        
        # Генерируем гендерно-зависимое сообщение от Гаспода
        gender_display = "мужчина" if gender == "male" else "женщина"
        gender_pronoun = "гражданин" if gender == "male" else "гражданка"
        
        gaspode_registered = f"""
🐺 **Отлично, {gender_pronoun} {user.first_name}!**

Гаспод записал: {gender_display}. Теперь все данные в протоколе Стражи.

**Программа исправления "Табекс" активирована!**

Каждые 2 часа к тебе будет наведываться кто-то из стражи для... *проверки*. 

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
        context.user_data['course_obj'] = new_course
        
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
