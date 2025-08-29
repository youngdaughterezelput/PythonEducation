|--	reports/
	|--run_report.sh
		|
		|--main.py
			|
			|--base_report.py
				|--daily_order_report.py
				|-- /*любой отчет*
			|--report_factory.py	
			|--mail_to.py



report_factory.py -- определяет класс отчета daily, weekly и тд на основе systemd service файла


!Если редактировали .env , то правим формат(удалить символы \r) sed -i 's/\r$//' .env

#проверить, что файлы существуют 
ls -la
# Проверьте права доступа
stat /opt/order_reports/setup.sh
# Также проверяем Python файлы на наличие \r
grep -l $'\r' *.py

# Если найдены, исправляем
sed -i 's/\r$//' *.py

# Быстрое исправление всех файлов в директории
find /opt/order_reports -type f -name "*.sh" -exec sed -i 's/\r$//' {} \;
find /opt/order_reports -type f -name "*.py" -exec sed -i 's/\r$//' {} \;

# Или для всех файлов
find /opt/order_reports -type f -exec sed -i 's/\r$//' {} \;


выдаем права на выполнение chmod +x run_report.sh setup.sh
mkdir -p /home/reports/logs
touch /home/reports/logs/order_reports.log
touch /home/reports/logs/email.log
chmod 644 /home/reports/logs/*.log

основная команда для выдачи прав в директории chmod +x /home/reports/run_report.sh

# Перезагрузите systemd конфигурацию
sudo systemctl daemon-reload

# Включите таймер для автозапуска
sudo systemctl enable daily-order-report.timer

# Запустите таймер
sudo systemctl start daily-order-report.timer

# Проверьте статус таймера
sudo systemctl status daily-order-report.timer

# Посмотрите список активных таймеров
systemctl list-timers

--------------------------------------------------------------
в директории /etc/systemd/system/

daily-report.service
daily-report.timer

находятся основные файлы запуска демона, где указан таймер запуска и директория запуска, команды для работы:
sudo systemctl enable daily-report.timer
sudo systemctl start daily-report.timer
sudo systemctl status daily-report.timer


# Просмотр активных таймеров
systemctl list-timers

# Просмотр логов сервиса
journalctl -u daily-report.service

