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

def send_email(has_attachment, attachment_path=None, report_date=None, report_name="Отчет по заказам OMNI", report_link="http://confluence.kifr-ru.local:8090/pages/viewpage.action?pageId=220467208"):
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
    msg['Subject'] = f"{report_name} за {date_str}"

    # Формируем тело письма
    if has_attachment and attachment_path and os.path.exists(attachment_path):
        main_body = f"Добрый день! Выгрузка за {date_str} во вложении."
        
        # Прикрепляем файл
        part = None
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        if part:
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)
            logging.info(f"Файл {attachment_path} прикреплен к письму")
    else:
        main_body = f"Добрый день! Выгрузка за {date_str} пустая."
        logging.info("Отчет пустой, файл не прикреплен")

    # Формируем HTML-версию письма с сепаратором
    html_content = f"""
<html>
<body>
    <p>{main_body}</p>
    
    <hr style="border: 1px solid #ddd; margin: 20px 0;">
    
    <p>С уважением,<br>
    Отдел поддержки омниканальной архитектуры<br>
    Почта: <a href="mailto:omni.support@hofftech.ru">omni.support@hofftech.ru</a></p>
    
    <p style="font-size: 12px; color: #666;">
    (Сервер: , Мониторинг: {report_name}, Инструкция: <a href="{report_link}">{report_link}</a>)
    </p>
</body>
</html>
"""

    # Добавляем HTML-версию письма
    msg.attach(MIMEText(html_content, 'html'))

    try:
        logging.info(f"Подключение к SMTP серверу {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        
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