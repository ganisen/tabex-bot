"""
Основной класс Telegram-бота для системы напоминаний о приёме лекарств Табекс.

Этот модуль содержит главный класс бота, который управляет всеми аспектами
взаимодействия с Telegram API и координирует работу всех сервисов.
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, ContextTypes
from telegram.constants import ParseMode

from config.settings import settings
from core.handlers.commands import setup_command_handlers
from core.handlers.callbacks import setup_callback_handlers
from database.connection import init_database

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tabex_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TabexBot:
    """
    Основной класс Telegram-бота для системы напоминаний о Табексе.
    
    Управляет жизненным циклом бота, регистрирует обработчики событий
    и координирует работу всех компонентов системы.
    """
    
    def __init__(self):
        """Инициализация бота с настройками из конфигурации."""
        self.app = None
        self.is_running = False
        logger.info("Инициализация Табекс-бота...")
    
    async def setup(self):
        """Настройка приложения и регистрация обработчиков."""
        try:
            # Создание приложения Telegram
            self.app = (
                Application.builder()
                .token(settings.bot_token)
                .build()
            )
            
            # Регистрация обработчиков команд
            setup_command_handlers(self.app)
            
            # Регистрация обработчиков callback-запросов
            setup_callback_handlers(self.app)
            
            logger.info("Настройка бота завершена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка при настройке бота: {e}")
            raise
    
    async def start(self):
        """Запуск бота."""
        if self.is_running:
            logger.warning("Попытка запуска уже работающего бота")
            return
        
        try:
            await self.setup()
            
            logger.info("Запуск Табекс-бота...")
            
            # Запуск polling с улучшенной обработкой ошибок
            await self.app.initialize()
            await self.app.start()
            
            # Добавляем глобальный обработчик ошибок
            self.app.add_error_handler(error_handler)
            
            # Запуск polling с сбросом pending обновлений
            await self.app.updater.start_polling(
                drop_pending_updates=True,
                poll_interval=1.0,  # Интервал между запросами
                timeout=10,         # Таймаут запроса
                bootstrap_retries=3  # Количество попыток повторного подключения
            )
            
            self.is_running = True
            logger.info("Табекс-бот успешно запущен и готов к работе!")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Остановка бота с таймаутом для graceful shutdown."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        try:
            logger.info("Остановка Табекс-бота...")
            
            if self.app and self.app.updater:
                try:
                    # Останавливаем updater с таймаутом
                    await asyncio.wait_for(
                        self.app.updater.stop(),
                        timeout=10.0
                    )
                    logger.info("Updater остановлен")
                except asyncio.TimeoutError:
                    logger.warning("Таймаут при остановке updater'а")
                except Exception as e:
                    logger.error(f"Ошибка при остановке updater'а: {e}")
            
            if self.app:
                try:
                    # Останавливаем приложение с таймаутом
                    await asyncio.wait_for(
                        self.app.stop(),
                        timeout=5.0
                    )
                    logger.info("Приложение остановлено")
                except asyncio.TimeoutError:
                    logger.warning("Таймаут при остановке приложения")
                except Exception as e:
                    logger.error(f"Ошибка при остановке приложения: {e}")
                
                try:
                    # Завершаем shutdown с таймаутом
                    await asyncio.wait_for(
                        self.app.shutdown(),
                        timeout=5.0
                    )
                    logger.info("Shutdown завершён")
                except asyncio.TimeoutError:
                    logger.warning("Таймаут при shutdown приложения")
                except Exception as e:
                    logger.error(f"Ошибка при shutdown: {e}")
            
            logger.info("Табекс-бот остановлен")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при остановке бота: {e}")
            # Принудительная остановка если что-то пошло не так
            self.is_running = False
    
    async def run_forever(self):
        """Запуск бота с обработкой сигналов для graceful shutdown."""
        try:
            await self.start()
            
            # Ожидание завершения работы
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания, остановка бота...")
        except Exception as e:
            logger.error(f"Неожиданная ошибка в работе бота: {e}")
        finally:
            await self.stop()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок."""
    logger.error("Исключение во время обработки обновления:", exc_info=context.error)
    
    # Если ошибка произошла при обработке сообщения пользователя
    if isinstance(update, Update) and update.message:
        try:
            await update.message.reply_text(
                "🔧 Произошла техническая ошибка. Попробуйте позже или обратитесь к администратору."
            )
        except Exception:
            # Если даже отправка сообщения об ошибке не удается
            logger.error("Не удалось отправить сообщение об ошибке пользователю")
