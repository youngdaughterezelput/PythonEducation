import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from dotenv import load_dotenv
from .database_connector import DatabaseConnector
from tkcalendar import DateEntry
from .report_set import ReportContextMenu
from icon_manager import IconManager

load_dotenv()

class BaseReportApp:
    """Базовый класс для отчетов с общими функциями"""
    def __init__(self, parent, report_name):
        self.window = ttk.Frame(parent, padding=10)
        # Инициализация менеджера иконок с передачей root
        self.icon_manager = IconManager()
        # Установка иконки
        self.icon_manager.set_icon(self)
        self.parent = parent
        self.report_name = report_name
        self.db_connector = None
        self.tree = None
        self.context_menu = None

    def create_date_range_controls(self):
        """Создает элементы управления для выбора диапазона дат"""
        date_frame = ttk.Frame(self.window)
        date_frame.pack(fill=tk.X, pady=5)
        
        # Виджет для выбора начальной даты
        ttk.Label(date_frame, text="Дата начала:").pack(side=tk.LEFT, padx=5)
        self.start_date = DateEntry(
            date_frame, 
            width=15, 
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd'
        )
        self.start_date.pack(side=tk.LEFT, padx=5)
        self.start_date.set_date(datetime.now())
        
        # Виджет для выбора конечной даты
        ttk.Label(date_frame, text="Дата окончания:").pack(side=tk.LEFT, padx=5)
        self.end_date = DateEntry(
            date_frame, 
            width=15, 
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd'
        )
        self.end_date.pack(side=tk.LEFT, padx=5)
        self.end_date.set_date(datetime.now())

    def create_report_button(self, text="Сформировать отчет", command=None):
        """Создает кнопку для генерации отчета"""
        ttk.Button(
            self.window, 
            text=text, 
            command=command or self.generate_report
        ).pack(pady=10)

    def create_results_table(self, columns):
        """Создает таблицу для вывода результатов с горизонтальной и вертикальной прокруткой"""
        # Основной фрейм для таблицы и прокруток
        table_frame = ttk.Frame(self.window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Создаем Treeview
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        # Настройка колонок
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.W)

        # Вертикальная прокрутка
        v_scroll = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=v_scroll.set)

        # Горизонтальная прокрутка
        h_scroll = ttk.Scrollbar(
            table_frame,
            orient=tk.HORIZONTAL,
            command=self.tree.xview
        )
        self.tree.configure(xscrollcommand=h_scroll.set)

        # Размещаем элементы с помощью grid
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # Настройка растягивания
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

    def get_report_data(self):
        """Возвращает данные для экспорта в Excel"""
        if not self.tree:
            return [], []
            
        # Получаем заголовки колонок
        columns = self.tree['columns']
        headers = [self.tree.heading(col)['text'] for col in columns]
        
        # Собираем данные из Treeview
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            data.append(values)
            
        return headers, data

    def clear_results(self):
        """Очищает результаты в таблице"""
        if self.tree:
            for item in self.tree.get_children():
                self.tree.delete(item)

    def generate_report(self):
        """Базовый метод генерации отчета (должен быть переопределен в дочерних классах)"""
        raise NotImplementedError("Метод generate_report должен быть реализован в дочернем классе")