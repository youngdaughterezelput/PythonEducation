import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from dotenv import load_dotenv
from .database_connector import DatabaseConnector
from tkcalendar import DateEntry
from .report_set import ReportContextMenu
from .base_app import BaseApp
from .baseSet import BaseReportApp

load_dotenv()

class OrderReportApp(BaseReportApp):
    """Класс для генерации отчета по заказам"""
    def __init__(self, parent):
        super().__init__(parent, "Отчет_по_заказам")
        
        # Настройки для отчета по заказам
        self.payment_conditions = ""
        self.delivery_conditions = ""
        self.excluded_names = """
            'Власов Вячеслав', 'Лучкова Ирина', 'Шилов Андрей', 
            'Никогосян Лидия', 'Сахаров Вячеслав', 'ывапыт Антоноввапы', 
            'Коуров Данил', 'Гаврилова Милена', 'Данилова Наталья', 
            'Власов Вячеслав Александрович', 'ОБЩЕСТВО*"ПРИВЕТ"',
            'vlasov ывфафыва', 'Вячеслав ывфафыва', 'Горюнов Александр'
        """
        
        self.load_settings()
        self.create_widgets()
        self.setup_database_connections()
        
        # Добавляем контекстное меню
        self.context_menu = ReportContextMenu(self.window, self)
        if self.tree:
            self.tree.bind("<Button-3>", self.context_menu.show)
    
    def setup_database_connections(self):
        """Настраивает подключения к базам данных"""
        # Основное подключение к ORDER БД
        self.db_connector = DatabaseConnector(prefix="ORDER", parent_window=self.window)
        if not self.db_connector.check_connection(self.window):
            messagebox.showwarning("Предупреждение", "Подключение к базе данных заказов не установлено!")
        else:
            # Подключения к дополнительным БД для типов оплаты и доставки
            self.payset_connector = DatabaseConnector(prefix="PAYSET", parent_window=self.window)
            self.delivery_connector = DatabaseConnector(prefix="DEL-ATOM", parent_window=self.window)
            
            # Проверяем подключения и загружаем условия
            self.check_and_load_conditions()
    
    def create_widgets(self):
        """Создает интерфейс для отчета по заказам"""
        # Заголовок
        ttk.Label(self.window, text="Отчет по заказам", font=("Arial", 14)).pack(pady=10)
        
        # Диапазон дат
        self.create_date_range_controls()
        
        # Кнопка генерации отчета
        self.create_report_button()
        
        # Таблица результатов
        columns = (
            "Способ оплаты", "Код способа оплаты", "Способ получения", "код ПВЗ//БЮ", 
            "Сумма заказа", "Номер заказа", "Статус", "Дата заказа", "ФИО"
        )
        self.create_results_table(columns)
    
    def check_and_load_conditions(self):
        """Проверяет подключения и загружает условия оплаты/доставки"""
        # Проверка подключения к PAYSET (типы оплаты)
        if not self.payset_connector.check_connection(self.window):
            messagebox.showwarning("Предупреждение", 
                "Подключение к базе типов оплаты не установлено! Используются значения по умолчанию.")
            self.set_default_payment_conditions()
        else:
            self.load_payment_conditions()
        
        # Проверка подключения к DEL-ATOM (типы доставки)
        if not self.delivery_connector.check_connection(self.window):
            messagebox.showwarning("Предупреждение", 
                "Подключение к базе типов доставки не установлено! Используются значения по умолчанию.")
            self.set_default_delivery_conditions()
        else:
            self.load_delivery_conditions()
    
    def load_payment_conditions(self):
        """Загружает условия оплаты из PAYSET БД"""
        try:
            payment_types = self.payset_connector.load_payment_types()
            self.payment_conditions = "\n".join([
                f"WHEN '{pt_id}' THEN '{pt_name}'" 
                for pt_id, pt_name in payment_types.items()
            ])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить типы оплаты:\n{str(e)}")
            self.set_default_payment_conditions()
    
    def load_delivery_conditions(self):
        """Загружает условия доставки из DEL-ATOM БД"""
        try:
            delivery_types = self.delivery_connector.load_delivery_types()
            self.delivery_conditions = "\n".join([
                f"WHEN '{dt_id}' THEN '{dt_name}'" 
                for dt_id, dt_name in delivery_types.items()
            ])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить типы доставки:\n{str(e)}")
            self.set_default_delivery_conditions()
    
    def set_default_payment_conditions(self):
        """Устанавливает значения по умолчанию для условий оплаты"""
        self.payment_conditions = """
            WHEN 'bankCard' THEN 'Банковская карта'
            WHEN 'qrCode' THEN 'Qr-код'
            WHEN 'onDelivery' THEN 'Наличными или при получении'
            WHEN 'yandexSplit' THEN 'Яндекс Сплит'
            WHEN 'sberSplit' THEN 'Сбер Сплит'
            WHEN 'yandexPay' THEN 'Яндекс Пэй'
            WHEN 'jurPerson' THEN 'Выставить счет ЮЛ'
            WHEN 'credit' THEN 'Кредитный брокер'
        """
    
    def set_default_delivery_conditions(self):
        """Устанавливает значения по умолчанию для условий доставки"""
        self.delivery_conditions = """
            WHEN '1' THEN 'Самовывоз'
            WHEN '2' THEN 'Доставка курьером'
            WHEN '5' THEN 'Доставка курьером'
            WHEN '4' THEN 'Самовывоз со склада'
            WHEN '8' THEN 'Самовывоз из ПВЗ'
        """
    
    def load_settings(self):
        """Загружает настройки из окружения при запуске приложения"""
        excluded_names = os.getenv("EXCLUDED_NAMES")
        if excluded_names:
            formatted_names = ", ".join([f"'{n.strip()}'" for n in excluded_names.split(",")])
            self.set_excluded_names(formatted_names)
    
    def get_excluded_names(self):
        """Преобразует SQL-формат исключенных имен в читаемый список"""
        return ", ".join([n.strip().strip("'") for n in self.excluded_names.split(",")])
    
    def set_excluded_names(self, names):
        """Устанавливает исключенные имена"""
        self.excluded_names = names
    
    def generate_report(self):
        """Генерация и вывод отчета по заказам с обработкой дубликатов"""
        start = self.start_date.get_date()
        end = self.end_date.get_date()
        
        # Форматирование дат в строки
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        
        # Формирование SQL-запроса
        query = f"""
        WITH FI AS (
            SELECT DISTINCT
                o.order_uid,
                CONCAT_WS(' ',
                    o.order_json->'shipment'->0->'userData'->>'lastName', 
                    o.order_json->'shipment'->0->'userData'->>'firstName'
                ) AS full_name
            FROM ordercmp."order" o
            WHERE 1=1
            AND o.order_status_id = 'CONFIRMED'
            AND '[{start_str}, {end_str}]'::daterange @> o.created_dt::date 
        )
        SELECT DISTINCT
            CASE o.payment_type_id
                {self.payment_conditions}
                ELSE 'Неизвестный способ (' || o.payment_type_id || ')'
            END,
            o.payment_type_id,
            CASE o.delivery_type_id
                {self.delivery_conditions}
                ELSE 'Неизвестный способ (' || o.delivery_type_id || ')'
            END,
            
            (o.order_json->'shipment'->0->'delivery'->>'pickPointId'),
            (o.order_json->'shipment'->0->>'totalAmountFinal')::numeric,
            o.order_num,
            os.order_status_name,
            o.created_dt::date,
            fi.full_name
            
        FROM ordercmp."order" o
        JOIN ordercmp.order_status os ON os.order_status_id = o.order_status_id
        LEFT JOIN ordercmp.order_payment op ON op.order_uid = o.order_uid
        JOIN FI fi ON fi.order_uid = o.order_uid
        WHERE 1=1 
            AND fi.full_name NOT IN ({self.excluded_names})
            AND NOT (fi.full_name ~* '.*(тест|test).*')
        ORDER BY o.order_num;
        """
        
        # Выполнение запроса и вывод результатов
        try:
            self.clear_results()
            
            # Выполнение запроса
            results = self.db_connector.execute_query(query)
            
            # Обработка дубликатов
            seen_orders = set()
            unique_results = []
            duplicate_count = 0
            
            for row in results:
                # Ключ для проверки дубликатов - номер заказа и дата
                order_key = (row[5], row[7])  # order_num и created_dt
                
                if order_key not in seen_orders:
                    seen_orders.add(order_key)
                    unique_results.append(row)
                else:
                    duplicate_count += 1
            
            # Заполнение таблицы только уникальными записями
            for row in unique_results:
                # Конвертация decimal в строку
                formatted_row = [
                    str(item) if isinstance(item, float) else item 
                    for item in row
                ]
                self.tree.insert("", tk.END, values=formatted_row)
                
            message = f"Найдено записей: {len(unique_results)}"
            if duplicate_count > 0:
                message += f" (дубликатов пропущено: {duplicate_count})"
            messagebox.showinfo("Успех", message)
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при выполнении запроса:\n{str(e)}")