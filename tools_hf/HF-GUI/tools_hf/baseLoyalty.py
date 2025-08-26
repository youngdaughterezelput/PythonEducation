from .base_app import BaseApp
from .database_connector import DatabaseConnector
from .soap_connector import SoapConnector
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta

class BaseLoyaltyApp(BaseApp):
    """Базовый класс для операций с лояльностью и купонами"""
    def __init__(self, parent, title):
        super().__init__(parent, title)
        self.db_connector = DatabaseConnector("ORDER")
        self.soap_connector = SoapConnector()
        self.soap_requests = {}
        self.current_params = None
        self.query_in_progress = False
        self.data = []
        
        self.check_db_connection()
        self.create_ui()
    
    def create_ui(self):
        """Создание интерфейса приложения"""
        self.create_db_connection_section()
        self.create_query_section()
        self.create_results_section()
        self.create_soap_generation_section()
        self.setup_context_menu()
    
    def check_db_connection(self):
        """Проверка подключения к БД"""
        if self.db_connector.check_connection(self.window):
            self.db_status.config(text="Статус БД: Подключено")
        else:
            self.db_status.config(text="Статус БД: Ошибка подключения")
    
    def setup_context_menu(self):
        """Настройка контекстного меню"""
        super().setup_context_menu()
        
        self.context_menu.add_command(
            label="Сформировать SOAP запрос", 
            command=self.generate_soap
        )
        
        self.soap_context_menu = tk.Menu(self.window, tearoff=0)
        self.soap_context_menu.add_command(
            label="Экспорт в Excel", 
            command=self.export_to_excel
        )
        self.soap_notebook.bind("<Button-3>", self.show_soap_context_menu)
    
    def show_soap_context_menu(self, event):
        """Показ контекстного меню для SOAP"""
        self.soap_context_menu.post(event.x_root, event.y_root)
    
    def validate_days(self, new_value):
        """Валидация ввода количества дней"""
        if new_value == "":
            return True
        try:
            value = int(new_value)
            return value >= 0
        except ValueError:
            return False
    
    def create_results_section(self):
        """Создание секции с результатами"""
        results_frame = ttk.LabelFrame(self.window, text="Результаты запроса", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Определение колонок будет в дочерних классах
        columns = self.get_columns()
        
        self.results_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )
        
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=100, anchor=tk.W)
        
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=v_scroll.set)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(xscroll=h_scroll.set)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bind_context_menu()
    
    def create_soap_generation_section(self):
        """Создание секции для SOAP запросов"""
        soap_frame = ttk.LabelFrame(self.window, text="SOAP-запросы", padding=10)
        soap_frame.pack(fill=tk.BOTH, padx=10, pady=5)
        
        self.soap_notebook = ttk.Notebook(soap_frame)
        self.soap_notebook.pack(fill=tk.BOTH, expand=True)
        
        default_frame = ttk.Frame(self.soap_notebook)
        self.soap_notebook.add(default_frame, text="Пустой запрос")
        
        self.soap_text = scrolledtext.ScrolledText(default_frame, width=100, height=15)
        self.soap_text.pack(fill=tk.BOTH, expand=True)
        self.soap_text.insert(tk.END, "<!-- Выберите запись для генерации SOAP -->")
        self.soap_text.config(state=tk.DISABLED)
    
    def execute_query(self):
        """Выполнение запроса с проверкой параметров"""
        if self.query_in_progress:
            messagebox.showwarning("Предупреждение", "Запрос уже выполняется")
            return

        try:
            self.query_in_progress = True
            self.execute_btn.config(state=tk.DISABLED)
            
            # Получаем текущие параметры
            current_params = self.get_current_params()
            
            # Проверяем, изменились ли параметры
            if self.current_params == current_params and self.data:
                if not messagebox.askyesno("Подтверждение", 
                                        "Параметры не изменились. Повторить запрос?"):
                    return
            
            self.current_params = current_params
            self._execute_query_with_params(current_params)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка выполнения запроса: {str(e)}")
        finally:
            self.query_in_progress = False
            self.execute_btn.config(state=tk.NORMAL)
    
    def process_requests(self):
        """Обработка SOAP запросов"""
        if not self.soap_requests:
            messagebox.showinfo("Информация", "Нет сгенерированных запросов")
            return
        
        if not self.soap_connector.check_auth():
            self.soap_connector.show_auth_dialog(self.window, self._process_requests)
            return
        
        self._process_requests()
    
    def _process_requests(self):
        """Внутренняя обработка SOAP запросов"""
        self.results = {}
        
        for item_id, soap_data in self.soap_requests.items():
            result = self.soap_connector.send_request(soap_data['soap'])
            result['request_id'] = soap_data['request_id']
            self.results[item_id] = result
            
            frame = ttk.Frame(self.soap_notebook)
            text_area = scrolledtext.ScrolledText(frame, width=100, height=15)
            text_area.pack(fill=tk.BOTH, expand=True)
            text_area.insert(tk.END, result['response'])
            text_area.config(state=tk.DISABLED)
            
            self.soap_notebook.add(frame, text=f"Ответ {result['request_id']}")
        
        for item_id in self.results:
            values = list(self.results_tree.item(item_id, "values"))
            result = self.results[item_id]['status']
            self.results_tree.item(item_id, values=values + [result])
        
        messagebox.showinfo("Готово", "Обработка запросов завершена")
    
    # Абстрактные методы, которые должны быть реализованы в дочерних классах
    def get_columns(self):
        """Возвращает список колонок для Treeview"""
        raise NotImplementedError()
    
    def get_current_params(self):
        """Возвращает текущие параметры запроса"""
        raise NotImplementedError()
    
    def _execute_query_with_params(self, params):
        """Выполняет запрос с указанными параметрами"""
        raise NotImplementedError()
    
    def generate_soap(self):
        """Генерация SOAP запросов"""
        raise NotImplementedError()
