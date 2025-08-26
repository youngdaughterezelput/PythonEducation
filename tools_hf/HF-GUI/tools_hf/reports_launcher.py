import tkinter as tk
from tkinter import ttk

from dotenv import load_dotenv
from .database_connector import DatabaseConnector
from .order_report import OrderReportApp

class ReportsLauncher:
    def __init__(self, parent):
        load_dotenv()
        
        self.window = ttk.Frame(parent, padding=10)
        self.parent = parent
        self.current_report = None
        
        self.create_widgets()
        self.load_reports()
    
    def create_widgets(self):
        """Создание элементов интерфейса для выбора отчетов"""
        # Заголовок
        ttk.Label(self.window, text="Система отчетов", font=("Arial", 14)).pack(pady=10)
        
        # Панель выбора отчетов
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(control_frame, text="Выберите отчет:").pack(side=tk.LEFT, padx=5)
        
        self.report_selector = ttk.Combobox(control_frame, state='readonly', width=40)
        self.report_selector.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.report_selector.bind("<<ComboboxSelected>>", self.change_report)
        
        # Контейнер для отчетов
        self.report_container = ttk.Frame(self.window)
        self.report_container.pack(fill=tk.BOTH, expand=True, pady=10)
    
    def load_reports(self):
        """Регистрация доступных отчетов"""
        self.reports = {
            "Отчет по заказам": OrderReportApp,
            # Здесь можно добавить другие отчеты:
            # "Другой отчет": OtherReportApp,
        }
        self.report_selector['values'] = list(self.reports.keys())
    
    def change_report(self, event=None):
        """Обработчик смены отчета"""
        # Закрываем текущий отчет
        if self.current_report:
            self.current_report.window.destroy()
            self.current_report = None
        
        # Получаем выбранный отчет
        report_name = self.report_selector.get()
        
        if report_name:
            report_class = self.reports.get(report_name)
            
            if report_class:
                # Создаем экземпляр отчета в контейнере
                self.current_report = report_class(self.report_container)
                self.current_report.window.pack(fill=tk.BOTH, expand=True)