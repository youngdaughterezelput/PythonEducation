from dotenv import load_dotenv
import pandas as pd
import os
from datetime import datetime

class BaseReport:
    def __init__(self):
        load_dotenv()
        self.report_name = "Отчет"
        
    def get_report_data(self):
        """Базовый метод, должен быть переопределен в дочерних классах"""
        return [], []
    
    def export_to_excel(self):
        """Экспорт данных отчета в Excel"""
        try:
            headers, data = self.get_report_data()
            
            if not headers or not data:
                return "Нет данных для экспорта"
            
            # Создаем DataFrame
            df = pd.DataFrame(data, columns=headers)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.report_name}_export_{timestamp}.xlsx"
            df.to_excel(filename, index=False)
            
            return f"Данные экспортированы в:\n{os.path.abspath(filename)}"
        except Exception as e:
            return f"Ошибка экспорта:\n{str(e)}"