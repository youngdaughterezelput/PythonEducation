import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from datetime import datetime
import logging

# Создаем директорию для логов, если она не существует
os.makedirs('logs', exist_ok=True)

# Настройка логирования для email
logging.basicConfig(
    filename='logs/email.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def send_email(has_attachment, attachment_path=None, report_date=None):
    # Настройки из переменных окружения
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.kifr-ru.local')
    smtp_port = int(os.getenv('SMTP_PORT', 25))
    from_addr = os.getenv('EMAIL_FROM', 'monitoring@hoff.ru')
    to_addrs = os.getenv('EMAIL_TO', '').split(',')  # список адресов через запятую

    if report_date is None:
        report_date = datetime.now()
    date_str = report_date.strftime("%Y-%m-%d")

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)
    msg['Subject'] = f"Отчет по заказам OMNI за {date_str}"

    # Проверяем существование файла в папке reports
    file_path = f"reports/{attachment_path}" if attachment_path else None
    if has_attachment and attachment_path and os.path.exists(attachment_path):
        body = f"Добрый день! Выгрузка за {date_str} во вложении."
        # Прикрепляем файл
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)
        logging.info(f"Файл {attachment_path} прикреплен к письму")
    else:
        body = f"Добрый день! Выгрузка за {date_str} пустая."
        logging.info("Отчет пустой, файл не прикреплен")

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Для порта 25 обычно не требуется TLS и аутентификация
        logging.info(f"Подключение к SMTP серверу {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        # Не используем starttls() и login() для порта 25 без аутентификации
        logging.info(f"Отправка письма от {from_addr} к {to_addrs}")
        server.sendmail(from_addr, to_addrs, msg.as_string())
        server.quit()
        
        success_msg = "Email отправлен успешно"
        print(success_msg)
        logging.info(success_msg)
        return True
        
    except Exception as e:
        error_msg = f"Ошибка отправки email: {str(e)}"
        print(error_msg)
        logging.error(error_msg)
        return False