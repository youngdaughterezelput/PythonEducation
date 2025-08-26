import psycopg2
import os
import tkinter as tk
from tkinter import ttk, messagebox
from .security_manager import SecurityManager
from typing import Dict, List, Optional, Union, Tuple

class DatabaseConnector:
    def __init__(self, prefix: str = None, parent_window: tk.Toplevel = None):
        """
        Инициализация подключения к базе данных
        
        :param prefix: Префикс для переменных окружения
        :param parent_window: Родительское окно для диалогов
        """
        self.connection = None
        self.prefix = self._determine_prefix(prefix, parent_window)
        self.parent_window = parent_window
        
        # Настройки подключения
        self.db_config = {
            'dbname': None,
            'user': None,
            'password': None,
            'host': None,
            'port': None
        }
        
        # Загружаем настройки при инициализации
        self._load_config()

    def _determine_prefix(self, prefix: str, parent_window: tk.Toplevel) -> str:
        """Определяет префикс подключения"""
        if prefix is not None:
            return prefix
            
        if parent_window is not None:
            return self._select_prefix(parent_window)
            
        return "BLLNG"  # Значение по умолчанию

    def _select_prefix(self, parent_window: tk.Toplevel) -> str:
        """Диалоговое окно выбора префикса подключения"""
        dialog = tk.Toplevel(parent_window)
        dialog.title("Выбор типа подключения")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Выберите тип подключения:").pack(pady=5)
        
        prefix_var = tk.StringVar(value="BLLNG")
        
        options = [
            ("Подключение к биллингу (BLLNG)", "BLLNG"),
            ("Подключение к заказам (ORDER)", "ORDER"),
            ("Подключение к настройкам оплаты (PAYSET)", "PAYSET"),
            ("Подключение к типам доставки (DEL-ATOM)", "DEL-ATOM")
        ]
        
        for text, value in options:
            ttk.Radiobutton(
                main_frame, 
                text=text,
                variable=prefix_var,
                value=value
            ).pack(anchor=tk.W)
        
        selected_prefix = None
        
        def on_confirm():
            nonlocal selected_prefix
            selected_prefix = prefix_var.get()
            dialog.destroy()
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Подтвердить", command=on_confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        parent_window.wait_window(dialog)
        return selected_prefix

    def _load_config(self) -> bool:
        """Загружает конфигурацию подключения из переменных окружения"""
        required_vars = [
            f'{self.prefix}_DB_NAME',
            f'{self.prefix}_DB_USER',
            f'{self.prefix}_DB_PASSWORD',
            f'{self.prefix}_DB_HOST',
            f'{self.prefix}_DB_PORT'
        ]
        
        # Получаем значения из защищенного хранилища или переменных окружения
        credentials = {}
        missing = []
        
        for var in required_vars:
            value = SecurityManager.get_password(var, 'env') or os.getenv(var)
            if value:
                credentials[var] = value
            else:
                missing.append(var)
        
        # Если есть недостающие параметры - показываем диалог
        if missing and self.parent_window:
            dialog = self._create_credentials_dialog(missing)
            self.parent_window.wait_window(dialog)
            
            if not hasattr(dialog, 'result') or not dialog.result:
                return False
                
            # Обновляем credentials с введенными значениями
            for var, value in dialog.result.items():
                credentials[var] = value
                os.environ[var] = value
                
                # Сохраняем в защищенное хранилище
                if dialog.save_var.get():
                    SecurityManager.store_password(var, value, 'env')
        
        # Заполняем конфиг
        if credentials:
            self.db_config = {
                'dbname': credentials.get(f'{self.prefix}_DB_NAME'),
                'user': credentials.get(f'{self.prefix}_DB_USER'),
                'password': credentials.get(f'{self.prefix}_DB_PASSWORD'),
                'host': credentials.get(f'{self.prefix}_DB_HOST'),
                'port': credentials.get(f'{self.prefix}_DB_PORT')
            }
            return True
            
        return False

    def _create_credentials_dialog(self, missing_vars: List[str]) -> tk.Toplevel:
        """Создает диалоговое окно для ввода учетных данных"""
        dialog = tk.Toplevel(self.parent_window)
        dialog.title(f"Настройки подключения ({self.prefix})")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Статус подключения
        self.db_status = ttk.Label(main_frame, text="Статус БД: Не проверено")
        self.db_status.pack(pady=5)
        
        # Поля для ввода
        entries = {}
        for var in missing_vars:
            frame = ttk.Frame(main_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=var.replace('_', ' ').title(), width=15).pack(side=tk.LEFT)
            entry = ttk.Entry(frame)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            entries[var] = entry
        
        # Чекбокс для сохранения настроек
        dialog.save_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            main_frame,
            text="Сохранить настройки",
            variable=dialog.save_var
        ).pack(pady=5, anchor=tk.W)
        
        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame,
            text="Подтвердить",
            command=lambda: self._on_dialog_submit(dialog, entries)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Отмена",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        return dialog

    def _on_dialog_submit(self, dialog: tk.Toplevel, entries: Dict[str, ttk.Entry]):
        """Обработчик подтверждения диалога"""
        dialog.result = {}
        
        for var, entry in entries.items():
            value = entry.get().strip()
            if not value:
                messagebox.showerror("Ошибка", f"Поле {var} обязательно для заполнения")
                return
                
            if var.endswith('_PORT'):
                try:
                    int(value)
                except ValueError:
                    messagebox.showerror("Ошибка", "Порт должен быть целым числом")
                    return
            
            dialog.result[var] = value
        
        dialog.destroy()

    def check_connection(self, parent_window: tk.Toplevel = None) -> bool:
        """Проверяет подключение к базе данных"""
        if parent_window:
            self.parent_window = parent_window
            
        if not self.db_config['dbname']:
            if not self._load_config():
                return False
        
        try:
            # Пробуем разные варианты подключения
            connection_urls = [
                # Основной вариант
                f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
                f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['dbname']}"
                "?sslmode=prefer",
                
                # Вариант с SSL
                f"postgresql://{self.db_config['user']}:{self.db_config['password']}@"
                f"{self.db_config['host']}:{self.db_config['port']}/{self.db_config['dbname']}"
                "?sslmode=require"
            ]
            
            for url in connection_urls:
                try:
                    self.connection = psycopg2.connect(url)
                    self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                    
                    if hasattr(self, 'db_status'):
                        self.db_status.config(text="Статус БД: Подключено", foreground="green")
                    
                    return True
                except psycopg2.Error as e:
                    continue
            
            # Если ни один вариант не сработал
            error_msg = "Не удалось подключиться к базе данных"
            if hasattr(self, 'db_status'):
                self.db_status.config(text=f"Статус БД: {error_msg}", foreground="red")
            
            messagebox.showerror("Ошибка подключения", error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Ошибка подключения: {str(e)}"
            if hasattr(self, 'db_status'):
                self.db_status.config(text=error_msg, foreground="red")
            
            messagebox.showerror("Ошибка подключения", error_msg)
            return False

    def execute_query(self, query: str, params: Tuple = None) -> List[Tuple]:
        """
        Выполняет SQL-запрос и возвращает результаты
        
        :param query: SQL-запрос
        :param params: Параметры для запроса (опционально)
        :return: Список кортежей с результатами
        """
        if not self.connection:
            if not self.check_connection():
                raise ConnectionError("Нет подключения к базе данных")
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except psycopg2.Error as e:
            error_msg = f"Ошибка выполнения запроса: {str(e)}"
            if self.parent_window:
                messagebox.showerror("Ошибка запроса", error_msg)
            raise DatabaseError(error_msg)
        
    def load_payment_types_rej(self):
        if self.prefix == "PAYSET":
            query = "SELECT payment_type_id FROM paysetat.payment_type ORDER BY payment_type_id"
        else:
            raise ValueError(f"Неизвестный префикс: {self.prefix}")

        results = self.execute_query(query)
        return [row[0] for row in results]  # Возвращаем только первый столбец (коды)
    

    def load_status_order(self):
        """Загружает статусы заказов и возвращает список допустимых значений"""
        if self.prefix == "ORDER":
            query = """
                SELECT order_status_id 
                FROM ordercmp.order_status 
                WHERE order_status_id IN ('NEW','EXPIRED') 
                ORDER BY order_status_id
            """
        else:
            raise ValueError(f"Неизвестный префикс: {self.prefix}")

        try:
            results = self.execute_query(query)
            return [row[0] for row in results] if results else ['EXPIRED', 'NEW']  # fallback
        except Exception as e:
            print(f"Ошибка загрузки статусов: {str(e)}")
            return ['EXPIRED']  # fallback значения

    def load_payment_types(self) -> Dict[str, str]:
        """Загружает типы оплаты из соответствующей базы данных"""
        if self.prefix == "PAYSET":
            query = """
                SELECT payment_type_id, payment_type_name 
                FROM paysetat.payment_type 
                ORDER BY payment_type_id
            """
        elif self.prefix == "ORDER":
            query = """
                SELECT DISTINCT payment_type_id, 
                CASE payment_type_id
                    WHEN 'bankCard' THEN 'Банковская карта'
                    WHEN 'qrCode' THEN 'Qr-код'
                    WHEN 'onDelivery' THEN 'Наличными или при получении'
                    WHEN 'yandexSplit' THEN 'Яндекс Сплит'
                    WHEN 'sberSplit' THEN 'Сбер Сплит'
                    WHEN 'yandexPay' THEN 'Яндекс Пэй'
                    WHEN 'jurPerson' THEN 'Выставить счет ЮЛ'
                    WHEN 'credit' THEN 'Кредитный брокер'
                    ELSE payment_type_id
                END as payment_type_name
                FROM ordercmp."order"
                WHERE payment_type_id IS NOT NULL
                ORDER BY payment_type_id
            """
        else:
            raise ValueError(f"Неизвестный префикс для загрузки типов оплаты: {self.prefix}")
            
        results = self.execute_query(query)
        return {row[0]: row[1] for row in results}

    def load_delivery_types(self) -> Dict[str, str]:
        """Загружает типы доставки из соответствующей базы данных"""
        if self.prefix == "DEL-ATOM":
            query = """
                SELECT delivery_type_id, name 
                FROM dlvatomc.delivery_type 
                ORDER BY delivery_type_id
            """
        elif self.prefix == "ORDER":
            query = """
                SELECT DISTINCT delivery_type_id, 
                CASE delivery_type_id
                    WHEN '1' THEN 'Самовывоз'
                    WHEN '2' THEN 'Доставка курьером'
                    WHEN '5' THEN 'Доставка курьером'
                    WHEN '4' THEN 'Самовывоз со склада'
                    WHEN '8' THEN 'Самовывоз из ПВЗ'
                    ELSE delivery_type_id
                END as delivery_type_name
                FROM ordercmp."order"
                WHERE delivery_type_id IS NOT NULL
                ORDER BY delivery_type_id
            """
        else:
            raise ValueError(f"Неизвестный префикс для загрузки типов доставки: {self.prefix}")
            
        results = self.execute_query(query)
        return {row[0]: row[1] for row in results}

    def close(self):
        """Закрывает соединение с базой данных"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        """Поддержка контекстного менеджера"""
        if not self.connection:
            self.check_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Поддержка контекстного менеджера"""
        self.close()


class DatabaseError(Exception):
    """Класс для ошибок базы данных"""
    pass