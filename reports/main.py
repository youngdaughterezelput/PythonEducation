from datetime import datetime, timedelta
from mail_to import send_email
import os
import logging
import re
import sys
import argparse
import time
from report_factory import ReportFactory


def load_env_file(filepath='.env'):
    """Загружает переменные из .env файла"""
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Ищем ключ и значение
                    match = re.match(r'([A-Za-z_0-9]+)=([^#]*)', line)
                    if match:
                        key, value = match.groups()
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
        logging.info("Переменные окружения загружены из .env файла")
    except FileNotFoundError:
        logging.warning(f"Файл {filepath} не найден. Используются системные переменные окружения.")
    except Exception as e:
        logging.error(f"Ошибка при загрузке .env файла: {str(e)}")

# Создаем директорию для логов
os.makedirs('logs', exist_ok=True)

# Настройка логирования
logging.basicConfig(
    filename='logs/order_reports.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    # Загружаем переменные из .env файла
    load_env_file()
    
    # Создаем директорию для отчетов
    os.makedirs('reports', exist_ok=True)
    
    # Создаем фабрику отчетов
    factory = ReportFactory()
    available_reports = factory.get_available_reports()
    logging.info(f"Доступные типы отчетов: {available_reports}")
    
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description='Генератор отчетов по заказам')
    if available_reports:
        parser.add_argument('--report-type', type=str, choices=available_reports,
                           help='Тип отчета для генерации')
    else:
        parser.add_argument('--report-type', type=str, help='Тип отчета для генерации')
    
    args = parser.parse_args()
    
    # Определяем тип отчета
    report_type = args.report_type
    
    # Если тип отчета не указан, пытаемся определить из systemd
    if not report_type:
        report_type = factory.detect_report_type_from_systemd()
        logging.info(f"Тип отчета определен из systemd: {report_type}")
    
    # Если тип отчета все еще не определен, используем значение по умолчанию
    if not report_type:
        report_type = 'daily'  # Значение по умолчанию
        logging.warning("Тип отчета не указан и не может быть определен из systemd. Используется значение по умолчанию: daily")
    
    # Проверяем, доступен ли выбранный тип отчета
    if report_type not in available_reports:
        logging.error(f"Тип отчета '{report_type}' недоступен. Доступные: {available_reports}")
        return False
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Определяем дату отчета (вчера)
            report_date = datetime.now() - timedelta(days=1)
            logging.info(f"Начало генерации отчета {report_type} за {report_date.strftime('%Y-%m-%d')}")
            
            # Создаем и генерируем отчет
            report = factory.get_report(report_type)
            filename, has_data = report.generate(report_date)
            logging.info(f"Отчет {report_type} сгенерирован: файл={filename}, есть_данные={has_data}")
            
            # Отправляем email с отчетом
            logging.info(f"Отправка email. Данные: {has_data}")
            email_sent = send_email(has_data, filename, report_date)
            
            if email_sent:
                logging.info("Email успешно отправлен")
            else:
                logging.warning("Не удалось отправить email")
            
            # Удаляем файл, если он создавался и мы его отправили
            if has_data and os.path.exists(f"reports/{filename}"):
                os.remove(f"reports/{filename}")
                logging.info(f"Файл reports/{filename} удален")
            
            logging.info(f"Отчет {report_type} успешно сгенерирован и отправлен")
            return True
            
        except Exception as e:
            retry_count += 1
            logging.error(f"Ошибка при выполнении отчета {report_type} (попытка {retry_count}/{max_retries}): {str(e)}", exc_info=True)
            
            if retry_count >= max_retries:
                logging.critical("Достигнуто максимальное количество попыток. Завершение работы.")
                return False
            
            # Ждем перед повторной попыткой (5 минут)
            logging.info("Ожидание 5 минут перед повторной попыткой")
            time.sleep(5 * 60)
    
    return False

if __name__ == "__main__":
    logging.info("Запуск сервиса генерации отчетов")
    success = main()
    sys.exit(0 if success else 1)