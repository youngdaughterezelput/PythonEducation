1) Структура 
2) Зависимости 
3) Запуск из python run.py
4) Установка зависимостей pip install -r requirements.txt
ИЛИ
pip install fastapi uvicorn sqlalchemy databases aiosqlite
5) Вариант запуска из uvicorn main:app --reload --host 0.0.0.0 --port 8000
6)Активация виртуального окружения 
    python -m venv venv
    source venv/bin/activate
7) После запуска приложения? получаем доступ к сваггеру http://localhost:8000/docs

8) ReDoc: http://localhost:8000/redoc