"""
Обработчики callback-запросов от inline-кнопок Telegram-бота.

Обрабатывает все взаимодействия пользователей с inline-клавиатурами,
такие как подтверждение приёма таблеток, навигация по меню и настройки.
"""
import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

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
        # Пока что обрабатываем только базовые callback'и
        # В следующих этапах здесь будет полноценная маршрутизация
        
        if callback_data == "placeholder":
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
