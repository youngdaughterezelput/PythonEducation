import os
import re
import importlib
import glob
import importlib.util
from base_report import BaseReport
import logging

# Настройка логирования
logging.basicConfig(
    filename='logs/factory.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ReportFactory:
    def __init__(self):
        self.report_classes = {}
        self.load_report_classes()
    
    def load_report_classes(self):
        """Динамически загружает все классы отчетов из текущей директории"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Ищем все файлы с отчетами
        report_files = glob.glob(os.path.join(current_dir, '*_report.py'))
        
        logging.info(f"Найдены файлы отчетов: {report_files}")
        
        for file_path in report_files:
            filename = os.path.basename(file_path)
            if filename != 'base_report.py':
                module_name = filename[:-3]
                
                try:
                    # Динамически импортируем модуль
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec is None:
                        logging.error(f"Не удалось создать spec для модуля {module_name}")
                        continue
                        
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Ищем классы отчетов
                    for name in dir(module):
                        obj = getattr(module, name)
                        try:
                            if (isinstance(obj, type) and 
                                issubclass(obj, BaseReport) and 
                                obj != BaseReport):
                                report_instance = obj()
                                report_type = report_instance.get_report_type()
                                self.report_classes[report_type] = obj
                                logging.info(f"Загружен класс отчета: {report_type} из {filename}")
                        except TypeError:
                            # Пропускаем объекты, которые не являются классами
                            continue
                        except Exception as e:
                            logging.error(f"Ошибка при проверке класса {name}: {e}")
                            
                except Exception as e:
                    logging.error(f"Ошибка загрузки модуля {module_name}: {e}", exc_info=True)
        
        logging.info(f"Загружено классов отчетов: {len(self.report_classes)}")
    
    def get_report(self, report_type):
        """Возвращает экземпляр класса отчета по типу"""
        if report_type in self.report_classes:
            return self.report_classes[report_type]()
        else:
            available = list(self.report_classes.keys())
            logging.error(f"Неизвестный тип отчета: {report_type}. Доступные: {available}")
            raise ValueError(f"Неизвестный тип отчета: {report_type}. Доступные: {available}")
    
    def get_available_reports(self):
        """Возвращает список доступных типов отчетов"""
        return list(self.report_classes.keys())
    
    def detect_report_type_from_systemd(self):
        """Определяет тип отчета на основе systemd service файла"""
        systemd_dir = "/etc/systemd/system"
        
        try:
            # Простой способ: используем аргументы командной строки
            import sys
            if len(sys.argv) > 1 and sys.argv[1] == '--report-type':
                if len(sys.argv) > 2:
                    return sys.argv[2]
            
            # Альтернативный способ: ищем service файлы
            if os.path.exists(systemd_dir):
                service_files = [f for f in os.listdir(systemd_dir) 
                               if f.endswith('.service') and 'order-report' in f]
                
                for service_file in service_files:
                    # Извлекаем тип отчета из имени файла
                    match = re.search(r'(\w+)-order-report\.service', service_file)
                    if match:
                        report_type = match.group(1)
                        logging.info(f"Определен тип отчета из systemd: {report_type}")
                        return report_type
            else:
                logging.warning(f"Директория systemd не существует: {systemd_dir}")
                        
        except Exception as e:
            logging.error(f"Ошибка определения типа отчета из systemd: {e}", exc_info=True)
        
        logging.warning("Не удалось определить тип отчета из systemd")
        return None