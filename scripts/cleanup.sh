#!/bin/bash

# Скрипт для очистки запущенных экземпляров Табекс-бота
# Останавливает все контейнеры и очищает блокировки

set -e

echo "🧹 Очистка экземпляров Табекс-бота..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 1. Остановка Docker контейнеров
print_status $YELLOW "📦 Остановка Docker контейнеров..."

# Останавливаем все контейнеры с именем tabex-bot
docker ps -q --filter "name=tabex-bot" | while read container_id; do
    if [ ! -z "$container_id" ]; then
        print_status $YELLOW "Остановка контейнера: $container_id"
        docker stop "$container_id" || true
    fi
done

# Удаляем остановленные контейнеры
docker ps -a -q --filter "name=tabex-bot" | while read container_id; do
    if [ ! -z "$container_id" ]; then
        print_status $YELLOW "Удаление контейнера: $container_id"
        docker rm "$container_id" || true
    fi
done

# 2. Docker Compose cleanup
if [ -f "docker-compose.yaml" ]; then
    print_status $YELLOW "🐳 Остановка через Docker Compose..."
    docker-compose down --remove-orphans || true
fi

# 3. Очистка lock файлов
print_status $YELLOW "🔒 Очистка файлов блокировок..."

# Локальные lock файлы
if [ -f "data/tabex-bot.lock" ]; then
    rm -f "data/tabex-bot.lock"
    print_status $GREEN "Удален локальный lock файл"
fi

# Lock файлы в /tmp (если скрипт запускается с правами)
if [ -f "/tmp/tabex-bot.lock" ]; then
    rm -f "/tmp/tabex-bot.lock" 2>/dev/null || true
    print_status $GREEN "Удален системный lock файл"
fi

# 4. Поиск запущенных процессов Python
print_status $YELLOW "🔍 Поиск запущенных процессов..."

# Ищем процессы с main.py или tabex
python_processes=$(ps aux | grep -E "(main\.py|tabex.*bot)" | grep -v grep | grep -v cleanup || true)

if [ ! -z "$python_processes" ]; then
    print_status $RED "⚠️  Найдены процессы Python:"
    echo "$python_processes"
    
    echo ""
    read -p "Хотите завершить эти процессы? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ps aux | grep -E "(main\.py|tabex.*bot)" | grep -v grep | grep -v cleanup | awk '{print $2}' | while read pid; do
            if [ ! -z "$pid" ]; then
                print_status $YELLOW "Завершение процесса PID: $pid"
                kill -TERM "$pid" 2>/dev/null || true
                sleep 2
                # Принудительное завершение если процесс не завершился
                kill -KILL "$pid" 2>/dev/null || true
            fi
        done
    fi
else
    print_status $GREEN "✅ Python процессы не найдены"
fi

# 5. Очистка логов (опционально)
if [ "$1" = "--clear-logs" ]; then
    print_status $YELLOW "📝 Очистка логов..."
    if [ -f "tabex_bot.log" ]; then
        > tabex_bot.log
        print_status $GREEN "Логи очищены"
    fi
fi

print_status $GREEN "✅ Очистка завершена!"

echo ""
echo "💡 Теперь можно безопасно запустить бота:"
echo "   docker-compose up tabex-bot"
echo "   или"
echo "   python main.py"
echo ""
