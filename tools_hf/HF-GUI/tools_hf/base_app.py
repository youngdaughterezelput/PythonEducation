import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pandas as pd
from datetime import datetime
from icon_manager import IconManager

class BaseApp:
    def __init__(self, parent, title):
        self.parent = parent
        self.window = ttk.Frame(parent)
        self.window.pack(fill=tk.BOTH, expand=True)
        # Инициализация менеджера иконок с передачей root
        self.icon_manager = IconManager()
        # Установка иконки
        self.icon_manager.set_icon(self)
        
        self.data = []
        self.results = {}
        self.context_menu_bound = False  # Инициализация атрибута
        
        self.setup_ui()
        self.setup_context_menu()
    
    def setup_ui(self):
        # Секции интерфейса
        self.create_db_connection_section()
        self.create_query_section()
        self.create_results_section()
        self.create_soap_generation_section()
    
    def create_db_connection_section(self):
        db_frame = ttk.Frame(self.window, padding=10)
        db_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.db_status = ttk.Label(db_frame, text="Статус БД: Не подключено")
        self.db_status.pack(side=tk.LEFT)
        
        ttk.Button(
            db_frame, 
            text="Проверить подключение", 
            command=self.check_db_connection
        ).pack(side=tk.RIGHT)
    
    def check_db_connection(self):
        # Должен быть переопределен в дочерних классах
        pass
    
    def create_query_section(self):
        # Должен быть переопределен в дочерних классах
        pass
    
    def create_results_section(self):
        # Должен быть переопределен в дочерних классах
        pass
    
    def create_soap_generation_section(self):
        # Должен быть переопределен в дочерних классах
        pass
    
    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.copy_menu = tk.Menu(self.context_menu, tearoff=0)
        self.context_menu.add_cascade(label="Копировать", menu=self.copy_menu)
        
        # Привязываем контекстное меню к Treeview
        self.results_tree.bind("<Button-3>", self.show_context_menu)
        self.results_tree.bind("<Button-1>", self.clear_selection)
    
    def bind_context_menu(self):
        if not self.context_menu_bound and hasattr(self, 'results_tree'):
            self.results_tree.bind("<Button-3>", self.show_context_menu)
            self.results_tree.bind("<Button-1>", self.clear_selection)
            self.context_menu_bound = True
    
    def show_context_menu(self, event):
        item = self.results_tree.identify_row(event.y)
        col = self.results_tree.identify_column(event.x)
        
        if item:
            self.copy_menu.delete(0, tk.END)
            
            col_id = int(col.replace('#', '')) - 1
            columns = self.results_tree['columns']
            if 0 <= col_id < len(columns):
                col_name = self.results_tree.heading(columns[col_id])['text']
                value = self.results_tree.item(item, 'values')[col_id]
                
                self.copy_menu.add_command(
                    label=f"Копировать '{col_name}'",
                    command=lambda: self.copy_to_clipboard(value)
                )
            
            self.copy_menu.add_command(
                label="Копировать всю строку",
                command=lambda: self.copy_row_to_clipboard(item)
            )
            
            self.context_menu.post(event.x_root, event.y_root)
    
    def copy_to_clipboard(self, text):
        self.window.clipboard_clear()
        self.window.clipboard_append(str(text))
        messagebox.showinfo("Успех", "Значение скопировано")
    
    def copy_row_to_clipboard(self, item):
        values = self.results_tree.item(item, 'values')
        row_text = "\t".join(str(v) for v in values)
        self.window.clipboard_clear()
        self.window.clipboard_append(row_text)
        messagebox.showinfo("Успех", "Строка скопирована")
    
    def clear_selection(self, event):
        for item in self.results_tree.selection():
            self.results_tree.selection_remove(item)
    
    def export_to_excel(self):
        if not self.data and not self.results:
            messagebox.showinfo("Информация", "Нет данных для экспорта")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exportData_unHolds_operations_{timestamp}.xlsx"
            
            export_data = []
            for item_id in self.results_tree.get_children():
                values = self.results_tree.item(item_id, "values")
                export_data.append(self._prepare_export_row(values))
            
            df = pd.DataFrame(export_data)
            df.to_excel(filename, index=False)
            messagebox.showinfo("Успех", f"Данные экспортированы в файл:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте данных:\n{str(e)}")
    
    def _prepare_export_row(self, values):
        # Должен быть переопределен в дочерних классах
        return {}