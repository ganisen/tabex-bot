@echo off
rem Скрипт быстрого запуска Tabex Bot через Docker для Windows
rem Автор: Tabex Bot Team

setlocal enabledelayedexpansion

echo 🚭 Tabex Bot - Docker Management Script (Windows)
echo ================================================

rem Проверка зависимостей
echo [INFO] Проверка системных зависимостей...

docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker не установлен. Установите Docker Desktop для Windows.
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose не установлен.
    pause
    exit /b 1
)

echo [SUCCESS] Все зависимости установлены

rem Определение команды
set "COMMAND=%~1"
if "%COMMAND%"=="" set "COMMAND=start"

rem Обработка команд
if /i "%COMMAND%"=="start" goto :start
if /i "%COMMAND%"=="stop" goto :stop  
if /i "%COMMAND%"=="restart" goto :restart
if /i "%COMMAND%"=="logs" goto :logs
if /i "%COMMAND%"=="status" goto :status
if /i "%COMMAND%"=="update" goto :update
goto :help

:start
echo [INFO] Проверка конфигурации...

rem Проверка .env файла
if not exist ".env" (
    echo [WARNING] .env файл не найден
    
    if exist ".env.example" (
        echo [INFO] Создание .env из .env.example...
        copy ".env.example" ".env"
        echo [WARNING] ВНИМАНИЕ: Отредактируйте .env файл и укажите BOT_TOKEN!
        echo [WARNING] Получить токен можно у @BotFather в Telegram
        
        rem Открываем файл для редактирования
        set /p "EDIT=Открыть .env для редактирования? (y/n): "
        if /i "!EDIT!"=="y" notepad .env
    ) else (
        echo [ERROR] .env.example файл не найден
        pause
        exit /b 1
    )
)

rem Создание директорий
echo [INFO] Создание необходимых директорий...
if not exist "data" mkdir data
if not exist "logs" mkdir logs

echo [SUCCESS] Директории созданы
echo [INFO] Сборка Docker образа...

docker-compose build --no-cache
if errorlevel 1 (
    echo [ERROR] Ошибка сборки образа
    pause
    exit /b 1
)

echo [SUCCESS] Образ собран успешно
echo [INFO] Запуск Tabex Bot...

docker-compose up -d
if errorlevel 1 (
    echo [ERROR] Ошибка запуска контейнера
    pause
    exit /b 1
)

echo [SUCCESS] 🚭 Tabex Bot запущен!
echo [INFO] Для просмотра логов: run.bat logs
echo [INFO] Для остановки: run.bat stop
goto :end

:stop
echo [INFO] Остановка Tabex Bot...
docker-compose down
echo [SUCCESS] Bot остановлен
goto :end

:restart
echo [INFO] Перезапуск Tabex Bot...
docker-compose down
timeout /t 2 /nobreak >nul
docker-compose up -d
echo [SUCCESS] Bot перезапущен
goto :end

:logs
echo [INFO] Логи Tabex Bot:
docker-compose logs -f tabex-bot
goto :end

:status
echo [INFO] Статус контейнеров:
docker-compose ps
echo.
echo [INFO] Использование ресурсов:
for /f "tokens=*" %%i in ('docker-compose ps -q') do (
    docker stats --no-stream %%i 2>nul
)
goto :end

:update
echo [INFO] Обновление из git репозитория...
git pull origin main
echo [INFO] Пересборка контейнера...
docker-compose build --no-cache
echo [INFO] Перезапуск...
docker-compose down
docker-compose up -d
echo [SUCCESS] Обновление завершено!
goto :end

:help
echo Использование: run.bat {start^|stop^|restart^|logs^|status^|update}
echo.
echo Команды:
echo   start   - Запустить bot (по умолчанию)
echo   stop    - Остановить bot
echo   restart - Перезапустить bot
echo   logs    - Показать логи
echo   status  - Показать статус
echo   update  - Обновить из git и перезапустить
goto :end

:end
pause
