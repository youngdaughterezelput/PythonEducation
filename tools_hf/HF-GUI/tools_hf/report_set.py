from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import re
import win32com.client as win32
import pandas as pd
from .database_connector import DatabaseConnector
from dotenv import load_dotenv, dotenv_values, set_key

class ReportContextMenu:
    def __init__(self, parent, report_app):
        self.parent = parent
        self.report_app = report_app
        self.menu = tk.Menu(parent, tearoff=0)
        
        self.menu.add_command(
            label="Экспорт в Excel", 
            command=self.export_to_excel
        )
        self.menu.add_command(
            label="Формировать письмо в Outlook", 
            command=self.compose_email
        )
        self.menu.add_separator()
        self.menu.add_command(
            label="Общие настройки", 
            command=self.open_settings
        )
    
    def show(self, event):
        self.menu.post(event.x_root, event.y_root)
    
    def compose_email(self):
        """Формирует письмо в Outlook в зависимости от типа отчета"""
        try:
            # Проверяем доступность Outlook
            try:
                outlook = win32.Dispatch("Outlook.Application")
            except Exception as e:
                messagebox.showerror(
                    "Ошибка Outlook", 
                    f"Не удалось подключиться к Outlook: {str(e)}\n\n"
                    "Убедитесь, что Microsoft Outlook установлен и настроен."
                )
                return
            
            # Экспортируем данные в Excel (тихий режим)
            export_success = self.export_to_excel(silent=True)
            if not export_success:
                return  # Экспорт не удался
            
            # Получаем путь к экспортированному файлу
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.report_app.report_name}_export_{timestamp}.xlsx"
            filepath = os.path.abspath(filename)
            
            # Определяем параметры письма по типу отчета
            match self.report_app.report_name:
                case "Отчет_по_заказам":
                    # Получаем даты из виджетов
                    start_date = self.report_app.start_date.get_date().strftime("%d.%m.%Y")
                    end_date = self.report_app.end_date.get_date().strftime("%d.%m.%Y")
                    
                    mail_params = {
                        "to": "Ekaterina.Tarasenko@hoff.ru",
                        "cc": "omni.support@hofftech.ru",
                        "subject": f"Выгрузка заказов за {start_date} - {end_date}",
                        "body": "Добрый день!\n\nВо вложении выгрузка заказов.\n\nС уважением,",
                        "attachments": [filepath]
                    }
                
                case _:
                    messagebox.showwarning(
                        "Неизвестный отчет",
                        "Для данного типа отчета не настроены параметры письма"
                    )
                    return
            
            # Создаем и наполняем письмо
            mail = outlook.CreateItem(0)
            mail.To = mail_params["to"]
            mail.CC = mail_params["cc"]
            mail.Subject = mail_params["subject"]
            mail.Body = mail_params["body"]
            
            for attachment in mail_params["attachments"]:
                if os.path.exists(attachment):
                    mail.Attachments.Add(attachment)
                else:
                    messagebox.showwarning(
                        "Файл не найден",
                        f"Файл вложения не найден:\n{attachment}"
                    )
            
            mail.Display(True)
            
        except Exception as e:
            messagebox.showerror(
                "Ошибка", 
                f"Ошибка при формировании письма:\n{str(e)}"
            )

    def export_to_excel(self, silent=False):
        """Экспортирует данные в Excel с опцией тихого режима"""
        try:
            # Проверяем наличие метода get_report_data
            if not hasattr(self.report_app, 'get_report_data') or not callable(self.report_app.get_report_data):
                if not silent:
                    messagebox.showerror(
                        "Ошибка экспорта", 
                        "Отчет не поддерживает экспорт в Excel"
                    )
                return False
            
            # Получаем данные из основного приложения
            headers, data = self.report_app.get_report_data()
            
            # Проверяем наличие данных
            if not headers or not data:
                if not silent:
                    messagebox.showinfo(
                        "Нет данных", 
                        "Нет данных для экспорта"
                    )
                return False
            
            # Создаем DataFrame
            df = pd.DataFrame(data, columns=headers)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Сохраняем в Excel
            filename = f"{self.report_app.report_name}_export_{timestamp}.xlsx"
            df.to_excel(filename, index=False)
            
            if not silent:
                messagebox.showinfo(
                    "Экспорт завершен", 
                    f"Данные успешно экспортированы в файл:\n{os.path.abspath(filename)}"
                )
            return True
        except Exception as e:
            if not silent:
                messagebox.showerror(
                    "Ошибка экспорта", 
                    f"Произошла ошибка при экспорте в Excel:\n{str(e)}"
                )
            return False
    
    def open_settings(self):
        SettingsWindow(self.parent, self.report_app)


class SettingsWindow(tk.Toplevel):

    ENV_FILE = '.env'

    def __init__(self, parent, report_app):
        super().__init__(parent)
        self.title("Настройки отчетов")
        self.geometry("800x600")
        self.report_app = report_app
        
        # Определяем путь к .env файлу В САМОМ НАЧАЛЕ
        self.env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.ENV_FILE)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладка для переменных окружения
        self.env_frame = ttk.Frame(self.notebook)
        #self.notebook.add(self.env_frame, text="Переменные окружения")
        
        # Вкладка для скриптов отчетов
        self.script_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.script_frame, text="Скрипты отчетов")
        self.create_script_tab()

        self.env_path = self.get_env_path()
        self.load_settings()
    
    def load_settings(self):
        """Загружает настройки из .env при запуске приложения"""
        # Исключенные имена
        excluded_names = os.getenv("EXCLUDED_NAMES")
        if excluded_names:
            formatted_names = ", ".join([f"'{n.strip()}'" for n in excluded_names.split(",")])
            self.set_excluded_names(formatted_names)

    def get_env_path(self):
        """Возвращает полный путь к .env файлу"""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), self.ENV_FILE)
    
    def create_env_tab(self):
        # Получаем все переменные окружения
        pass
    
    def save_env_changes(self):
        messagebox.showinfo("Сохранение", "Изменения сохранены")
    
    def create_script_tab(self):
        ttk.Label(self.script_frame, text="Выберите отчет:").pack(pady=5, anchor=tk.W)
        
        self.report_selector = ttk.Combobox(
            self.script_frame, 
            values=["Отчет по заказам", "Другой отчет"],
            state="readonly"
        )
        self.report_selector.pack(fill=tk.X, padx=5, pady=5)
        self.report_selector.set("Отчет по заказам")
        self.report_selector.bind("<<ComboboxSelected>>", self.load_report_settings)
        
        self.settings_container = ttk.Frame(self.script_frame)
        self.settings_container.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.load_report_settings()
    
    def load_report_settings(self, event=None):
        for widget in self.settings_container.winfo_children():
            widget.destroy()
        
        report_name = self.report_selector.get()
        
        if report_name == "Отчет по заказам":
            self.create_order_report_settings()
    
    def create_order_report_settings(self):
        # Загружаем текущие настройки из .env
        env_vars = dotenv_values(self.env_path)
        
        names_frame = ttk.LabelFrame(self.settings_container, text="Исключенные имена")
        names_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(names_frame, text="Список имен через запятую:").pack(anchor=tk.W)
        self.names_entry = ttk.Entry(names_frame)
        self.names_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Исключенные имена
        excluded_names = env_vars.get("EXCLUDED_NAMES", "")
        if not excluded_names:
            # Если в .env нет, берем из приложения и конвертируем в удобный формат
            sql_names = self.report_app.get_excluded_names()
            excluded_names = ", ".join([n.strip().strip("'") for n in sql_names.split(",")])
        self.names_entry.insert(0, excluded_names)
        
        ttk.Button(
            names_frame,
            text="Сохранить изменения",
            command=self.save_excluded_names
        ).pack(pady=5)
    
    def update_payment_types(self):
        try:
            db_connector = DatabaseConnector(prefix="PAYSET")
            
            # Проверяем подключение без автоматического показа диалога
            if not db_connector.check_connection():
                # Если подключения нет, предлагаем настроить его
                if messagebox.askyesno(
                    "Ошибка подключения",
                    "Нет подключения к PAYSET базе данных. Хотите настроить подключение сейчас?",
                    parent=self
                ):
                    # Показываем диалог настройки
                    db_connector.show_db_dialog(self)
                    # Повторно проверяем подключение после настройки
                    if not db_connector.check_connection():
                        messagebox.showerror("Ошибка", "Не удалось установить подключение к PAYSET базе данных")
                        return
                else:
                    return
            
            # Загружаем актуальные способы оплаты
            payment_types = db_connector.load_paysettype_types()
            
            # Формируем новые условия
            new_conditions = []
            for ptype_id, ptype_name in payment_types.items():
                new_conditions.append(f"WHEN '{ptype_id}' THEN '{ptype_name}'")
            
            new_conditions_str = "\n    ".join(new_conditions)
            
            # Обновляем текстовое поле
            self.payment_text.config(state=tk.NORMAL)
            self.payment_text.delete(1.0, tk.END)
            self.payment_text.insert(tk.END, new_conditions_str)
            self.payment_text.config(state=tk.DISABLED)

            # Обновляем .env файл
            set_key(
                self.env_path,
                "PAYMENT_CONDITIONS",
                new_conditions_str
            )
            
            # Обновляем текущее окружение
            os.environ["PAYMENT_CONDITIONS"] = new_conditions_str
            
            # Сохраняем в классе отчета
            self.report_app.set_payment_conditions(new_conditions_str)
            
            messagebox.showinfo("Успех", "Способы оплаты успешно обновлены")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при обновлении способов оплаты:\n{str(e)}")
    
    
    def save_excluded_names(self):
        names = self.names_entry.get().strip()
        if not names:
            messagebox.showwarning("Предупреждение", "Список имен не может быть пустым")
            return
        
        # Сохраняем в .env файл
        set_key(self.env_path, "EXCLUDED_NAMES", names)
        
        # Обновляем текущее окружение
        os.environ["EXCLUDED_NAMES"] = names
        
        # Форматируем имена для SQL
        formatted_names = ", ".join([f"'{n.strip()}'" for n in names.split(",")])
        
        # Сохраняем в классе отчета
        self.report_app.set_excluded_names(formatted_names)
        
        messagebox.showinfo("Успех", "Список исключенных имен обновлен и сохранен")