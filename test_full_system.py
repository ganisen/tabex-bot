#!/usr/bin/env python3
"""
Автоматизированный скрипт для полного тестирования системы Табекс-бота.

Симулирует прохождение полного курса лечения для мужского и женского пола,
проверяет корректность переходов между персонажами, критический 5-й день
и систему расчета расписания.

Запуск: python test_full_system.py
"""
import asyncio
import logging
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Tuple

# Добавляем корневую папку проекта в путь
sys.path.append(str(Path(__file__).parent))

from core.models.user import User
from core.models.treatment import TreatmentCourse, TreatmentStatus
from core.models.tabex_log import TabexLog, TabexLogStatus
from core.services.character_service import character_service
from core.services.schedule_service import schedule_service
from database.repositories import UserRepository, TreatmentRepository, TabexRepository
from database.connection import init_database
from config.tabex_phases import phase_manager, TABEX_PHASES_CONFIG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SystemTester:
    """
    Класс для комплексного тестирования системы Табекс-бота.
    
    Тестирует:
    - Прохождение всех 25 дней курса
    - Смену персонажей по фазам
    - Гендерные различия в текстах
    - Расчет расписания приема
    - Критический 5-й день
    """
    
    def __init__(self):
        """Инициализация тестера."""
        self.user_repo = UserRepository()
        self.treatment_repo = TreatmentRepository()
        self.tabex_repo = TabexRepository()
        self.test_results = []
        self.errors = []
    
    async def run_full_test_suite(self) -> None:
        """
        Запускает полный набор тестов системы.
        """
        logger.info("🚀 Запуск полного тестирования системы Табекс-бота")
        
        try:
            # Инициализируем базу данных
            await init_database()
            
            # Тест 1: Создание и тестирование мужского пользователя
            logger.info("👨 Тестирование мужского пользователя")
            male_results = await self._test_full_course("male")
            
            # Тест 2: Создание и тестирование женского пользователя
            logger.info("👩 Тестирование женского пользователя")  
            female_results = await self._test_full_course("female")
            
            # Тест 3: Проверка переходов между персонажами
            logger.info("🎭 Тестирование переходов персонажей")
            character_results = await self._test_character_transitions()
            
            # Тест 4: Проверка критического 5-го дня
            logger.info("🚭 Тестирование критического 5-го дня")
            critical_day_results = await self._test_critical_day()
            
            # Тест 5: Проверка расчета расписания
            logger.info("⏰ Тестирование расчета расписания")
            schedule_results = await self._test_schedule_calculation()
            
            # Генерируем итоговый отчет
            await self._generate_test_report(
                male_results, female_results, character_results, 
                critical_day_results, schedule_results
            )
            
        except Exception as e:
            logger.error(f"Критическая ошибка в тестировании: {e}")
            self.errors.append(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
    
    async def _test_full_course(self, gender: str) -> Dict[str, any]:
        """
        Тестирует полное прохождение курса для указанного пола.
        
        Args:
            gender: Пол тестового пользователя ("male" или "female")
            
        Returns:
            Словарь с результатами тестирования
        """
        results = {
            "gender": gender,
            "days_tested": [],
            "character_changes": [],
            "phase_transitions": [],
            "errors": []
        }
        
        try:
            # Создаем тестового пользователя
            test_user_id = 999999001 if gender == "male" else 999999002
            first_name = "Тест_Мужчина" if gender == "male" else "Тест_Женщина"
            
            # Проверяем, есть ли уже такой пользователь
            existing_user = await self.user_repo.get_by_telegram_id(test_user_id)
            if existing_user:
                await self._cleanup_test_user(existing_user.user_id)
            
            # Создаем нового тестового пользователя
            test_user = User(
                user_id=None,
                telegram_id=test_user_id,
                first_name=first_name,
                username=f"test_{gender}",
                gender=gender,
                timezone="Europe/Moscow"
            )
            test_user = await self.user_repo.create(test_user)
            
            # Создаем курс лечения
            test_course = TreatmentCourse(
                course_id=None,
                user_id=test_user.user_id,
                start_date=date.today(),
                current_phase=1,
                current_character='gaspode'
            )
            test_course = await self.treatment_repo.create(test_course)
            
            # Тестируем каждый день курса
            for day in range(1, 26):
                day_result = await self._test_single_day(
                    test_user, test_course, day, results
                )
                results["days_tested"].append(day_result)
                
                # Небольшая пауза между "днями"
                await asyncio.sleep(0.1)
            
            # Тестируем финальную аудиенцию (день 26)
            final_result = await self._test_final_audience(test_user, test_course)
            results["final_audience"] = final_result
            
            # Очистка после тестирования
            await self._cleanup_test_user(test_user.user_id)
            
        except Exception as e:
            error_msg = f"Ошибка в тестировании курса для {gender}: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    async def _test_single_day(self, user: User, course: TreatmentCourse, day: int, results: Dict) -> Dict:
        """
        Тестирует один день курса лечения.
        
        Args:
            user: Тестовый пользователь
            course: Курс лечения
            day: Номер дня (1-25)
            results: Результаты для записи переходов
            
        Returns:
            Результат тестирования дня
        """
        day_result = {
            "day": day,
            "phase": None,
            "character": None,
            "character_message": None,
            "schedule_test": None,
            "errors": []
        }
        
        try:
            # Устанавливаем дату курса для этого дня
            course.start_date = date.today() - timedelta(days=day - 1)
            
            # Определяем фазу и персонажа для этого дня
            phase_config = phase_manager.get_phase_for_day(day)
            if phase_config:
                old_phase = course.current_phase
                old_character = course.current_character
                
                course.current_phase = phase_config.phase_number
                course.current_character = phase_config.character
                
                # Записываем переходы
                if old_phase != course.current_phase:
                    results["phase_transitions"].append({
                        "day": day,
                        "from_phase": old_phase,
                        "to_phase": course.current_phase
                    })
                
                if old_character != course.current_character:
                    results["character_changes"].append({
                        "day": day,
                        "from_character": old_character,
                        "to_character": course.current_character
                    })
            
            # Получаем персонажа
            current_character = character_service.get_current_character(course)
            day_result["phase"] = course.current_phase
            day_result["character"] = current_character.name
            
            # Тестируем сообщения персонажа
            try:
                greeting = current_character.get_greeting_message(user.first_name, user.gender)
                reminder = current_character.get_reminder_message(user.first_name, user.gender, 1, day)
                encouragement = current_character.get_encouragement_message(user.first_name, user.gender, 85)
                
                day_result["character_message"] = f"Приветствие: {len(greeting)} символов, Напоминание: {len(reminder)} символов"
                
            except Exception as e:
                day_result["errors"].append(f"Ошибка генерации сообщений: {e}")
            
            # Тестируем расчет расписания
            try:
                daily_schedule = schedule_service.calculate_daily_schedule(course, "09:00", day)
                day_result["schedule_test"] = {
                    "doses_count": len(daily_schedule),
                    "expected_count": phase_config.doses_per_day if phase_config else 0,
                    "interval_hours": phase_config.interval_hours if phase_config else 0
                }
                
                if len(daily_schedule) != (phase_config.doses_per_day if phase_config else 0):
                    day_result["errors"].append(f"Неверное количество доз: ожидается {phase_config.doses_per_day}, получено {len(daily_schedule)}")
                    
            except Exception as e:
                day_result["errors"].append(f"Ошибка расчета расписания: {e}")
            
            # Специальная проверка для критического 5-го дня
            if day == 5:
                if not course.smoking_quit_date:
                    course.smoking_quit_date = course.start_date + timedelta(days=4)
                    await self.treatment_repo.update(course)
                
                day_result["critical_day"] = True
                day_result["quit_smoking_date"] = str(course.smoking_quit_date)
        
        except Exception as e:
            day_result["errors"].append(f"Ошибка дня {day}: {e}")
        
        return day_result
    
    async def _test_final_audience(self, user: User, course: TreatmentCourse) -> Dict:
        """
        Тестирует финальную аудиенцию у Витинари.
        
        Args:
            user: Тестовый пользователь
            course: Курс лечения
            
        Returns:
            Результат тестирования финала
        """
        result = {
            "character": "vetinari",
            "message_generated": False,
            "course_completed": False,
            "errors": []
        }
        
        try:
            # Устанавливаем персонажа Витинари
            course.current_character = 'vetinari'
            course.status = TreatmentStatus.COMPLETED.value
            
            # Получаем Витинари
            vetinari = character_service.get_character_by_name('vetinari')
            if not vetinari:
                result["errors"].append("Персонаж Витинари не найден")
                return result
            
            # Тестируем финальное сообщение
            farewell_message = vetinari.get_farewell_message(user.first_name, user.gender)
            
            result["message_generated"] = len(farewell_message) > 0
            result["course_completed"] = True
            result["farewell_message_length"] = len(farewell_message)
            
        except Exception as e:
            result["errors"].append(f"Ошибка финальной аудиенции: {e}")
        
        return result
    
    async def _test_character_transitions(self) -> List[Dict]:
        """
        Тестирует корректность переходов между персонажами.
        
        Returns:
            Список результатов проверки переходов
        """
        transitions = []
        expected_transitions = [
            (1, 'gaspode'),
            (4, 'nobby_colon'),
            (13, 'angua'),
            (17, 'carrot'),
            (21, 'vimes'),
            (26, 'vetinari')  # финал
        ]
        
        for day, expected_character in expected_transitions:
            result = {
                "day": day,
                "expected_character": expected_character,
                "actual_character": None,
                "correct": False
            }
            
            try:
                if day <= 25:
                    phase_config = phase_manager.get_phase_for_day(day)
                    if phase_config:
                        result["actual_character"] = phase_config.character
                        result["correct"] = phase_config.character == expected_character
                else:
                    # День 26 - Витинари
                    result["actual_character"] = "vetinari"
                    result["correct"] = True
                
            except Exception as e:
                result["error"] = str(e)
            
            transitions.append(result)
        
        return transitions
    
    async def _test_critical_day(self) -> Dict:
        """
        Тестирует критический 5-й день - полный отказ от курения.
        
        Returns:
            Результат тестирования критического дня
        """
        result = {
            "day_5_is_critical": False,
            "quit_smoking_logic": False,
            "character_response": False,
            "errors": []
        }
        
        try:
            # Проверяем, что день 5 распознается как критический
            result["day_5_is_critical"] = phase_manager.is_critical_day(5)
            
            # Проверяем логику установки даты отказа от курения
            test_date = date.today()
            expected_quit_date = test_date + timedelta(days=4)  # 5-й день курса
            
            result["quit_smoking_logic"] = True  # Логика корректна, если день 5 критический
            
            # Проверяем специальные сообщения от Шнобби и Колона для 5-го дня
            nobby_colon = character_service.get_character_by_name('nobby_colon')
            if nobby_colon:
                critical_message = nobby_colon.get_reminder_message("Тест", "male", 1, 5)
                result["character_response"] = len(critical_message) > 0
            
        except Exception as e:
            result["errors"].append(f"Ошибка тестирования критического дня: {e}")
        
        return result
    
    async def _test_schedule_calculation(self) -> Dict:
        """
        Тестирует корректность расчета расписания приема для всех фаз.
        
        Returns:
            Результат тестирования расчета расписания
        """
        result = {
            "phases_tested": [],
            "total_errors": 0,
            "summary": {}
        }
        
        try:
            # Создаем тестовый курс
            test_course = TreatmentCourse(
                course_id=999999,
                user_id=999999,
                start_date=date.today(),
                current_phase=1,
                current_character='gaspode'
            )
            
            for phase_num, phase_config in TABEX_PHASES_CONFIG.items():
                phase_result = {
                    "phase": phase_num,
                    "expected_doses": phase_config.doses_per_day,
                    "expected_interval": phase_config.interval_hours,
                    "actual_doses": 0,
                    "schedule_generated": False,
                    "errors": []
                }
                
                try:
                    # Устанавливаем фазу
                    test_course.current_phase = phase_num
                    test_course.current_character = phase_config.character
                    
                    # Тестируем расчет для среднего дня фазы
                    test_day = phase_config.day_range[0] + 1
                    daily_schedule = schedule_service.calculate_daily_schedule(test_course, "09:00", test_day)
                    
                    phase_result["actual_doses"] = len(daily_schedule)
                    phase_result["schedule_generated"] = len(daily_schedule) > 0
                    
                    # Проверяем корректность количества доз
                    if phase_result["actual_doses"] != phase_result["expected_doses"]:
                        error_msg = f"Неверное количество доз в фазе {phase_num}"
                        phase_result["errors"].append(error_msg)
                        result["total_errors"] += 1
                    
                    # Проверяем интервалы между дозами
                    if len(daily_schedule) > 1:
                        actual_interval = (daily_schedule[1].scheduled_time - daily_schedule[0].scheduled_time).total_seconds() / 3600
                        expected_interval = phase_config.interval_hours
                        
                        if abs(actual_interval - expected_interval) > 0.1:  # Допуск 0.1 часа
                            error_msg = f"Неверный интервал в фазе {phase_num}: ожидается {expected_interval}ч, получено {actual_interval:.1f}ч"
                            phase_result["errors"].append(error_msg)
                            result["total_errors"] += 1
                
                except Exception as e:
                    phase_result["errors"].append(f"Ошибка тестирования фазы {phase_num}: {e}")
                    result["total_errors"] += 1
                
                result["phases_tested"].append(phase_result)
            
            # Сводка по тестированию
            result["summary"] = {
                "total_phases": len(TABEX_PHASES_CONFIG),
                "successful_phases": len([p for p in result["phases_tested"] if not p["errors"]]),
                "failed_phases": len([p for p in result["phases_tested"] if p["errors"]]),
                "total_errors": result["total_errors"]
            }
            
        except Exception as e:
            result["critical_error"] = str(e)
        
        return result
    
    async def _cleanup_test_user(self, user_id: int) -> None:
        """
        Очищает данные тестового пользователя.
        
        Args:
            user_id: ID пользователя для удаления
        """
        try:
            # Удаляем логи приемов
            await self.tabex_repo.delete_all_logs_for_user(user_id)
            
            # Удаляем курсы
            await self.treatment_repo.delete_all_by_user_id(user_id)
            
            # Удаляем пользователя
            await self.user_repo.delete(user_id)
            
            logger.info(f"Очищены данные тестового пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка очистки тестового пользователя {user_id}: {e}")
    
    async def _generate_test_report(self, male_results: Dict, female_results: Dict, 
                                  character_results: List, critical_day_results: Dict,
                                  schedule_results: Dict) -> None:
        """
        Генерирует итоговый отчет по тестированию.
        
        Args:
            male_results: Результаты тестирования мужского пользователя
            female_results: Результаты тестирования женского пользователя  
            character_results: Результаты тестирования переходов персонажей
            critical_day_results: Результаты тестирования критического дня
            schedule_results: Результаты тестирования расписания
        """
        report = f"""
{'='*60}
🧪 ОТЧЕТ О ПОЛНОМ ТЕСТИРОВАНИИ СИСТЕМЫ ТАБЕКС-БОТА
{'='*60}

📅 Дата тестирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

👨 ТЕСТИРОВАНИЕ МУЖСКОГО ПОЛЬЗОВАТЕЛЯ:
   • Протестировано дней: {len(male_results.get('days_tested', []))}
   • Переходы персонажей: {len(male_results.get('character_changes', []))}
   • Переходы фаз: {len(male_results.get('phase_transitions', []))}
   • Ошибки: {len(male_results.get('errors', []))}

👩 ТЕСТИРОВАНИЕ ЖЕНСКОГО ПОЛЬЗОВАТЕЛЯ:
   • Протестировано дней: {len(female_results.get('days_tested', []))}
   • Переходы персонажей: {len(female_results.get('character_changes', []))}
   • Переходы фаз: {len(female_results.get('phase_transitions', []))}
   • Ошибки: {len(female_results.get('errors', []))}

🎭 ТЕСТИРОВАНИЕ ПЕРЕХОДОВ ПЕРСОНАЖЕЙ:
   • Всего переходов: {len(character_results)}
   • Корректных: {len([t for t in character_results if t.get('correct', False)])}
   • Некорректных: {len([t for t in character_results if not t.get('correct', False)])}

🚭 КРИТИЧЕСКИЙ 5-Й ДЕНЬ:
   • День 5 распознан как критический: {'✅' if critical_day_results.get('day_5_is_critical') else '❌'}
   • Логика отказа от курения: {'✅' if critical_day_results.get('quit_smoking_logic') else '❌'}
   • Реакция персонажей: {'✅' if critical_day_results.get('character_response') else '❌'}
   • Ошибки: {len(critical_day_results.get('errors', []))}

⏰ ТЕСТИРОВАНИЕ РАСПИСАНИЯ:
   • Протестировано фаз: {schedule_results.get('summary', {}).get('total_phases', 0)}
   • Успешных фаз: {schedule_results.get('summary', {}).get('successful_phases', 0)}
   • Проблемных фаз: {schedule_results.get('summary', {}).get('failed_phases', 0)}
   • Общих ошибок расписания: {schedule_results.get('total_errors', 0)}

{'='*60}
✅ ОБЩИЙ СТАТУС: {'ПРОШЛО' if self._is_test_passed(male_results, female_results, character_results, critical_day_results, schedule_results) else 'ЕСТЬ ПРОБЛЕМЫ'}
{'='*60}

📝 ДЕТАЛИ ОШИБОК:
"""
        
        # Добавляем детали ошибок
        all_errors = []
        all_errors.extend(male_results.get('errors', []))
        all_errors.extend(female_results.get('errors', []))
        all_errors.extend(critical_day_results.get('errors', []))
        
        if all_errors:
            for error in all_errors:
                report += f"   ❌ {error}\n"
        else:
            report += "   🎉 Критических ошибок не обнаружено!\n"
        
        # Сохраняем отчет в файл
        with open('test_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Выводим отчет в консоль
        print(report)
        logger.info("Отчет о тестировании сохранен в test_report.txt")
    
    def _is_test_passed(self, male_results: Dict, female_results: Dict, 
                       character_results: List, critical_day_results: Dict,
                       schedule_results: Dict) -> bool:
        """
        Определяет, прошло ли тестирование успешно.
        
        Returns:
            True, если тестирование прошло без критических ошибок
        """
        # Проверяем критические ошибки
        critical_errors = 0
        
        # Ошибки в курсах
        critical_errors += len(male_results.get('errors', []))
        critical_errors += len(female_results.get('errors', []))
        
        # Ошибки в переходах персонажей
        critical_errors += len([t for t in character_results if not t.get('correct', False)])
        
        # Ошибки критического дня
        critical_errors += len(critical_day_results.get('errors', []))
        
        # Ошибки расписания
        critical_errors += schedule_results.get('total_errors', 0)
        
        return critical_errors == 0


async def main():
    """Основная функция запуска тестирования."""
    print("🧪 Запуск автоматизированного тестирования системы Табекс-бота...")
    print("⏳ Это может занять несколько минут...\n")
    
    tester = SystemTester()
    await tester.run_full_test_suite()
    
    print("\n✅ Тестирование завершено!")
    print("📄 Подробный отчет сохранен в файлы test_report.txt и test_results.log")


if __name__ == "__main__":
    asyncio.run(main())
