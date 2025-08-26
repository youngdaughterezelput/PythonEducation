#!/bin/bash

# Переходим в директорию со скриптом
cd /home/reports

# Активируем виртуальное окружение
source venv/bin/activate

# Загружаем переменные окружения из файла .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "$(date): Переменные окружения загружены из .env"
fi

# Создаем директории для логов, если они не существуют
mkdir -p logs
mkdir -p reports

echo "$(date): Запуск генерации отчета по заказам..."

# Проверка зависимостей в виртуальном окружении
if ! python -c "import psycopg2" 2>/dev/null; then
    echo "ОШИБКА: Библиотека psycopg2 не установлена в виртуальном окружении"
    exit 1
fi

# Определяем тип отчета из аргументов
REPORT_TYPE=""
if [ $# -gt 0 ]; then
    REPORT_TYPE="--report-type $1"
    echo "$(date): Используется тип отчета: $1"
fi

# Запуск Python скрипта
echo "$(date): Запуск main.py $REPORT_TYPE"
python main.py $REPORT_TYPE

# Сохраняем код выхода
EXIT_CODE=$?

# Дективируем виртуальное окружение
deactivate

echo "$(date): Завершение работы с кодом: $EXIT_CODE"
exit $EXIT_CODE