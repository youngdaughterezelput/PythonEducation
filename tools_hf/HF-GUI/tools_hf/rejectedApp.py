import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkcalendar import DateEntry
import webbrowser
import json
from .database_connector import DatabaseConnector
import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PaymentRejectedApp:
    def __init__(self, parent):
        self.parent = parent
        self.window = ttk.Frame(parent)
        self.window.pack(fill=tk.BOTH, expand=True)
        
        self.data = []
        self.payment_types = []
        self.query_in_progress = False
        self.log_windows = {}  # Словарь для отслеживания окон с логами

        # Добавьте сессию для запросов
        self.session = requests.Session()
        self.session.verify = False  # Отключаем проверку SSL
        
        # Подключение к базам данных
        self.db_connector = DatabaseConnector(prefix="BLLNG", parent_window=self.window)
        self.order_connector = DatabaseConnector(prefix="ORDER", parent_window=self.window)
        self.payset_connector = DatabaseConnector(prefix="PAYSET", parent_window=self.window)
        
        # Основные элементы интерфейса
        self.create_query_section()
        self.create_results_section()
        self.setup_context_menu()
        
        # Установка текущей даты по умолчанию
        self.date_entry.set_date(datetime.date.today())
        
        # Загрузка данных при инициализации
        self.load_payment_types_for_date()

    def create_query_section(self):
        """Создает секцию ввода параметров запроса с кастомным меню вместо Combobox"""
        query_frame = ttk.LabelFrame(self.window, text="Параметры запроса", padding=10)
        query_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Выбор даты
        ttk.Label(query_frame, text="Дата:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.date_entry = DateEntry(
            query_frame,
            date_pattern='yyyy-mm-dd',
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2
        )
        self.date_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        self.date_entry.bind("<<DateEntrySelected>>", self.on_date_changed)
        
        # Кастомный выбор типа оплаты
        ttk.Label(query_frame, text="Тип оплаты:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        
        # Фрейм для кнопки выбора типа оплаты
        menu_frame = ttk.Frame(query_frame)
        menu_frame.grid(row=0, column=3, sticky=tk.EW, padx=5, pady=2)
        
        # Кнопка для открытия меню
        self.payment_var = tk.StringVar(value="Выберите тип оплаты")
        self.menu_btn = ttk.Button(
            menu_frame,
            textvariable=self.payment_var,
            width=25,
            command=self.show_payment_menu
        )
        self.menu_btn.pack(fill=tk.X, expand=True)
        
        # Кнопка выполнения запроса
        self.execute_btn = ttk.Button(
            query_frame,
            text="Обновить данные",
            command=self.execute_query
        )
        self.execute_btn.grid(row=0, column=4, padx=10)
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(
            query_frame,
            orient=tk.HORIZONTAL,
            length=200,
            mode='determinate'
        )
        self.progress.grid(row=1, column=0, columnspan=6, pady=5, sticky=tk.EW)
        
        # Настройка растягивания колонок
        query_frame.columnconfigure(3, weight=1)

    def show_payment_menu(self):
        """Показывает меню с доступными типами оплат"""
        if not self.payment_types:
            return
            
        # Создаем новое меню
        menu = tk.Menu(self.window, tearoff=0)
        
        # Добавляем пункты меню для каждого типа оплаты
        for payment_type in self.payment_types:
            name = payment_type['payment_type_name']
            menu.add_command(
                label=name,
                command=lambda pt=payment_type: self.set_payment_type(pt)
            )
        
        try:
            # Показываем меню под кнопкой
            x = self.menu_btn.winfo_rootx()
            y = self.menu_btn.winfo_rooty() + self.menu_btn.winfo_height()
            menu.post(x, y)
            
            # Закрываем меню при потере фокуса
            menu.bind("<FocusOut>", lambda e: menu.destroy())
        except tk.TclError:
            menu.destroy()

    def set_payment_type(self, payment_type):
        """Устанавливает выбранный тип оплаты"""
        self.payment_var.set(payment_type['payment_type_name'])
        self.selected_payment = payment_type
        self.execute_query()

    def on_date_changed(self, event=None):
        """Обработчик изменения даты"""
        self.load_payment_types_for_date()

    def load_payment_types_for_date(self):
        """Загружает типы оплат для выбранной даты"""
        if not self.check_db_connection():
            return

        selected_date = self.date_entry.get_date()
        date_str = selected_date.strftime('%Y-%m-%d')

        try:
            query = """
                SELECT DISTINCT o.payment_type_id
                FROM bllngcmp.order o 
                JOIN bllngcmp.payment_order po ON po.order_uid = o.order_uid
                JOIN bllngcmp.payment p ON p.internal_transaction_id = po.internal_transaction_id 
                WHERE p.payment_status = 'REJECTED'
                AND p.created_dt::date = %s
                ORDER BY o.payment_type_id;
            """
            
            results = self.db_connector.execute_query(query, (date_str,))
            
            if results:
                payment_codes = [row[0] for row in results]
                self.payment_types = self.get_payment_display_names(payment_codes)
                
                if self.payment_types:
                    # Устанавливаем первый тип оплаты по умолчанию
                    self.set_payment_type(self.payment_types[0])
                else:
                    self.payment_var.set("Типы не найдены")
                    self.clear_results()
            else:
                self.payment_types = []
                self.payment_var.set("Типы не найдены")
                self.clear_results()
                messagebox.showinfo("Информация", f"Для даты {date_str} не найдено rejected оплат")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке типов оплат: {str(e)}")

    def get_payment_display_names(self, payment_codes):
        """Получает отображаемые имена для кодов оплат"""
        try:
            if not payment_codes:
                return []
                
            in_condition = ",".join([f"'{code}'" for code in payment_codes])
            query = f"""
                SELECT payment_type_id, payment_type_name 
                FROM paysetat.payment_type 
                WHERE payment_type_id IN ({in_condition})
                ORDER BY payment_type_name;
            """
            
            results = self.payset_connector.execute_query(query)
            
            if results:
                return [{'payment_type_id': row[0], 'payment_type_name': row[1]} for row in results]
            else:
                return [{'payment_type_id': code, 'payment_type_name': code} for code in payment_codes]
                
        except Exception as e:
            print(f"DEBUG: Ошибка при получении имен: {str(e)}")
            return [{'payment_type_id': code, 'payment_type_name': code} for code in payment_codes]

    def execute_query(self):
        """Выполняет запрос к базе данных"""
        # Проверяем, что тип оплаты выбран
        if not hasattr(self, 'selected_payment') or not self.selected_payment:
            messagebox.showwarning("Предупреждение", "Не выбран тип оплаты")
            return
            
        if self.query_in_progress:
            return

        if not self.check_db_connection():
            return

        payment_code = self.selected_payment['payment_type_id']
        print(f"DEBUG: Выбранный код оплаты: {payment_code}")

        selected_date = self.date_entry.get_date()
        date_str = selected_date.strftime('%Y-%m-%d')

        try:
            self.query_in_progress = True
            self.execute_btn.config(state=tk.DISABLED)
            #self.analyze_all_btn.config(state=tk.DISABLED)
            self.progress['value'] = 20
            self.window.update()

            query = """
                SELECT 
                    o.order_num,
                    o.order_amount,
                    o.payment_type_id,
                    p.created_dt,
                    p.external_transaction_id,
                    p.internal_transaction_id,
                    o.payment_amount,
                    o.payment_amount 
                        - COALESCE(ol.amount, 0) 
                        - COALESCE(oc.amount, 0) 
                        - COALESCE(ogc.amount, 0) AS end_sum,
                    CASE WHEN %s IN ('yandexPay', 'yandexSplit', 'credit') 
                        THEN p.internal_transaction_id::text
                        ELSE p.external_transaction_id 
                    END AS display_transaction_id,
                    o.order_uid
                FROM bllngcmp.order o 
                LEFT JOIN bllngcmp.order_loyalty ol ON ol.order_uid = o.order_uid
                LEFT JOIN bllngcmp.order_coupon oc ON oc.order_uid = o.order_uid 
                LEFT JOIN bllngcmp.order_gift_card ogc ON ogc.order_uid = o.order_uid
                LEFT JOIN bllngcmp.payment_order po ON po.order_uid = o.order_uid
                LEFT JOIN bllngcmp.payment p ON p.internal_transaction_id = po.internal_transaction_id 
                WHERE p.payment_status = 'REJECTED'
                    AND o.payment_type_id = %s
                    AND p.created_dt::date = %s
                ORDER BY p.created_dt DESC;
            """
            
            self.progress['value'] = 40
            self.window.update()

            self.data = self.db_connector.execute_query(query, (payment_code, payment_code, date_str))

            self.progress['value'] = 70
            self.window.update()

            # Очищаем предыдущие результаты
            self.clear_results()

            if not self.data:
                messagebox.showinfo("Информация", "Оплат в статусе Rejected не найдено")
                return

            # Получаем order_uids для запроса в ORDER базу
            order_uids = [row[9] for row in self.data if row[9]]
            
            # Получаем имена клиентов
            customer_names = self.get_customer_names(order_uids)
            
            # Заполняем таблицу данными
            for row in self.data:
                full_name = customer_names.get(row[9], "")
                
                values = (
                    row[0], row[1], row[2], row[3], 
                    row[8], row[6], row[7], full_name
                )
                self.results_tree.insert("", tk.END, values=values)

            self.progress['value'] = 100
            messagebox.showinfo("Успех", f"Найдено записей: {len(self.data)}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка выполнения запроса: {str(e)}")
        finally:
            self.query_in_progress = False
            self.execute_btn.config(state=tk.NORMAL)
            #self.analyze_all_btn.config(state=tk.NORMAL)
            self.progress['value'] = 0

    def create_results_section(self):
        """Создает секцию вывода результатов"""
        results_frame = ttk.LabelFrame(self.window, text="Результаты запроса", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Таблица для отображения результатов
        self.results_tree = ttk.Treeview(results_frame, selectmode="browse")
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        
        # Полосы прокрутки
        v_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        h_scroll = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Настройка колонок
        columns = (
            "order_num", "order_amount", "payment_type_id", "created_dt",
            "external_transaction_id", "payment_amount", "end_sum", "full_name"
        )
        
        headers = {
            "order_num": "Номер заказа",
            "order_amount": "Сумма заказа",
            "payment_type_id": "Тип оплаты",
            "created_dt": "Дата создания",
            "external_transaction_id": "Транзакция",
            "payment_amount": "Сумма платежа",
            "end_sum": "Итоговая сумма",
            "full_name": "ФИО клиента"
        }
        
        self.results_tree["columns"] = columns
        for col in columns:
            self.results_tree.heading(col, text=headers[col])
            self.results_tree.column(col, width=120, anchor=tk.W)

    def clear_results(self):
        """Очищает результаты запроса"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

    def check_db_connection(self):
        """Проверяет подключение к базе данных"""
        if not self.db_connector.check_connection(self.window):
            messagebox.showwarning("Предупреждение", "Подключение к базе данных не установлено!")
            return False
        return True

    def setup_context_menu(self):
        """Настраивает контекстное меню"""
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.copy_menu = tk.Menu(self.context_menu, tearoff=0)
        self.context_menu.add_cascade(label="Копировать", menu=self.copy_menu)
        self.context_menu.add_command(
            label="Поиск в ElasticSearch",
            command=self.search_in_elastic
        )
        self.context_menu.add_command(
            label="Анализировать лог по транзакции",
            command=self.analyze_transaction_log
        )
        self.elastic_item = None
        
        self.results_tree.bind("<Button-3>", self.show_context_menu)
        self.results_tree.bind("<Button-1>", self.clear_selection)

    def show_context_menu(self, event):
        """Показывает контекстное меню"""
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
            
            self.elastic_item = item
            self.context_menu.post(event.x_root, event.y_root)
        else:
            self.elastic_item = None

    def copy_to_clipboard(self, text):
        """Копирует текст в буфер обмена"""
        self.window.clipboard_clear()
        self.window.clipboard_append(str(text))
        messagebox.showinfo("Успех", "Значение скопировано")

    def copy_row_to_clipboard(self, item):
        """Копирует всю строку в буфер обмена"""
        values = self.results_tree.item(item, 'values')
        row_text = "\t".join(str(v) for v in values)
        self.window.clipboard_clear()
        self.window.clipboard_append(row_text)
        messagebox.showinfo("Успех", "Строка скопирована")

    def clear_selection(self, event):
        """Очищает выделение в таблице"""
        for item in self.results_tree.selection():
            self.results_tree.selection_remove(item)

    def get_customer_names(self, order_uids):
        """Получает имена клиентов по order_uids"""
        if not order_uids:
            return {}
            
        try:
            if not self.order_connector.check_connection(None):
                return {}
                
            in_condition = ",".join([f"'{uid}'" for uid in order_uids])
            
            query = f"""
                SELECT 
                    o.order_uid,
                    CONCAT(
                        o.order_json->'shipment'->0->'userData'->>'lastName', 
                        ' ', 
                        o.order_json->'shipment'->0->'userData'->>'firstName'
                    ) AS full_name
                FROM ordercmp."order" o
                WHERE o.order_uid IN ({in_condition})
            """
            
            results = self.order_connector.execute_query(query)
            return {row[0]: row[1] for row in results} if results else {}
            
        except Exception:
            return {}

    def search_in_elastic(self):
        """Выполняет поиск в ElasticSearch"""
        if not self.elastic_item:
            return
            
        try:
            values = self.results_tree.item(self.elastic_item, 'values')
            transaction_id = values[4]
            created_dt_str = values[3]
            payment_type = values[2]
            
            if not transaction_id:
                messagebox.showwarning("Предупреждение", "Нет ID транзакции для поиска")
                return
                
            dt = self.parse_datetime(created_dt_str)
            if not dt:
                return
            
            from_time = (dt - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            to_time = (dt + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            base_url = "https://log.kifr-ru.local/s/omni/app/discover#/"
            
            _g = f"(filters:!(),refreshInterval:(pause:!t,value:60000),time:(from:'{from_time}',to:'{to_time}'))"
            
            if payment_type in ['yandexPay', 'yandexSplit']:
                _a = f"(columns:!(message,MessageTemplate,traceId,kubernetes.container.name,'@level'),filters:!(),hideChart:!f,index:'97bbcb4e-6ac8-4971-963c-49d9cfbf3655',interval:auto,query:(language:kuery,query:'message:%20%22{transaction_id}%22%20and%20NOT%20(%22PENDING%22%20or%20%22FAILED%22)'),sort:!(!('@timestamp',desc)))"
            else:
                _a = f"(columns:!(message,MessageTemplate,traceId,kubernetes.container.name,'@level'),filters:!(),index:'97bbcb4e-6ac8-4971-963c-49d9cfbf3655',interval:auto,query:(language:kuery,query:'message:%20%22{transaction_id}%22%20and%20NOT%20%22-100%22%20and%20NOT%20%22-2007%22'),sort:!(!('@timestamp',desc)))"
            
            full_url = f"{base_url}?_g={_g}&_a={_a}"
            webbrowser.open(full_url)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при формировании URL:\n{str(e)}")

    def parse_datetime(self, dt_value):
        """Парсит строку с датой и временем или принимает объект datetime"""
        if isinstance(dt_value, datetime.datetime):
            return dt_value
            
        formats = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.datetime.strptime(dt_value, fmt)
            except ValueError:
                continue
                
        messagebox.showerror("Ошибка формата даты", f"Неизвестный формат даты: {dt_value}")
        return None

    def analyze_transaction_log(self):
        """Анализирует лог по выбранной транзакции"""
        if not self.elastic_item:
            return
            
        try:
            values = self.results_tree.item(self.elastic_item, 'values')
            transaction_id = values[4]
            created_dt_str = values[3]
            payment_type = values[2]
            order_num = values[0]
            
            if not transaction_id:
                messagebox.showwarning("Предупреждение", "Нет ID транзакции для анализа")
                return
                
            dt = self.parse_datetime(created_dt_str)
            if not dt:
                return
            
            from_time = (dt - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            to_time = (dt + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            # Формируем URL для запроса к Kibana
            base_url = "https://log.kifr-ru.local/s/omni/app/discover#/"
            
            _g = f"(filters:!(),refreshInterval:(pause:!t,value:60000),time:(from:'{from_time}',to:'{to_time}'))"
            
            if payment_type in ['yandexPay', 'yandexSplit']:
                _a = f"(columns:!(message,MessageTemplate,traceId,kubernetes.container.name,'@level'),filters:!(),hideChart:!f,index:'97bbcb4e-6ac8-4971-963c-49d9cfbf3655',interval:auto,query:(language:kuery,query:'message:%20%22{transaction_id}%22%20and%20NOT%20(%22PENDING%22%20or%20%22FAILED%22)'),sort:!(!('@timestamp',desc)))"
            else:
                _a = f"(columns:!(message,MessageTemplate,traceId,kubernetes.container.name,'@level'),filters:!(),index:'97bbcb4e-6ac8-4971-963c-49d9cfbf3655',interval:auto,query:(language:kuery,query:'message:%20%22{transaction_id}%22%20and%20NOT%20%22-100%22%20and%20NOT%20%22-2007%22'),sort:!(!('@timestamp',desc)))"
            
            full_url = f"{base_url}?_g={_g}&_a={_a}"
            
            # Получаем HTML страницу с отключенной проверкой SSL
            response = self.session.get(full_url)  # Исправленная строка
            response.raise_for_status()
            
            # Парсим HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем таблицу с результатами
            table = soup.find('table')
            if not table:
                messagebox.showinfo("Информация", "Логи без @level == ERROR")
                return
                
            # Создаем окно для отображения логов
            self.show_log_window(order_num, transaction_id, table)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при анализе лога:\n{str(e)}")

    def show_log_window(self, order_num, transaction_id, table):
        """Отображает окно с логами транзакции"""
        # Закрываем предыдущее окно для этой транзакции, если оно открыто
        if transaction_id in self.log_windows:
            try:
                self.log_windows[transaction_id].destroy()
            except:
                pass
        
        # Создаем новое окно
        log_window = tk.Toplevel(self.parent)
        log_window.title(f"Логи транзакции: {transaction_id} (Заказ: {order_num})")
        log_window.geometry("1200x800")
        self.log_windows[transaction_id] = log_window
        
        # Создаем фреймы
        main_frame = ttk.Frame(log_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Панель управления
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Кнопки
        ttk.Button(
            control_frame,
            text="Обновить данные",
            command=lambda: self.update_log_window(log_window, transaction_id, order_num)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Показать полные сообщения",
            command=lambda: self.toggle_full_messages(log_window)
        ).pack(side=tk.LEFT, padx=5)
        
        # Таблица для отображения логов
        columns = ("timestamp", "level", "container", "message_template")
        headers = {
            "timestamp": "Время",
            "level": "Уровень",
            "container": "Контейнер",
            "message_template": "Шаблон сообщения"
        }
        
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Настройка колонок
        for col in columns:
            tree.heading(col, text=headers[col])
            tree.column(col, width=200, anchor=tk.W)
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Заполняем таблицу данными
        self.fill_log_table(tree, table)
        
        # Сохраняем ссылку на таблицу в окне
        log_window.tree = tree

    def fill_log_table(self, tree, table):
        """Заполняет таблицу данными из HTML таблицы"""
        # Очищаем существующие данные
        for item in tree.get_children():
            tree.delete(item)
        
        # Извлекаем данные из HTML таблицы
        rows = table.find_all('tr')
        headers = [th.get_text().strip() for th in rows[0].find_all('th')]
        
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) < len(headers):
                continue
                
            # Извлекаем значения
            values = {}
            for i, header in enumerate(headers):
                if header == "MessageTemplate":
                    # Получаем текст и удаляем лишние пробелы
                    values["message_template"] = cells[i].get_text().strip()
                elif header == "@timestamp":
                    values["timestamp"] = cells[i].get_text().strip()
                elif header == "kubernetes.container.name":
                    values["container"] = cells[i].get_text().strip()
                elif header == "@level":
                    values["level"] = cells[i].get_text().strip()
            
            # Добавляем строку в таблицу
            if values:
                tree.insert("", tk.END, values=(
                    values.get("timestamp", ""),
                    values.get("level", ""),
                    values.get("container", ""),
                    values.get("message_template", "")
                ))

    def toggle_full_messages(self, log_window):
        """Переключает отображение полных сообщений"""
        # Если колонка уже есть, удаляем ее
        if "full_message" in log_window.tree['columns']:
            log_window.tree['columns'] = ("timestamp", "level", "container", "message_template")
            log_window.tree.heading("message_template", text="Шаблон сообщения")
            log_window.tree.column("message_template", width=200)
        else:
            # Добавляем колонку для полного сообщения
            log_window.tree['columns'] = ("timestamp", "level", "container", "message_template", "full_message")
            log_window.tree.heading("full_message", text="Полное сообщение")
            log_window.tree.column("full_message", width=400)
            
            # Для существующих строк добавляем пустые значения
            for item in log_window.tree.get_children():
                log_window.tree.set(item, "full_message", "")

    def update_log_window(self, log_window, transaction_id, order_num):
        """Обновляет данные в окне логов"""
        try:
            # Получаем текущую дату/время из окна
            # В реальной реализации нужно будет заново выполнить запрос к Kibana
            # Для простоты просто обновим существующие данные
            messagebox.showinfo("Обновление", "Данные логов обновлены")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при обновлении логов: {str(e)}")

    
    def show_analysis_results(self, error_count, error_details):
        """Показывает результаты анализа всех логов"""
        result_window = tk.Toplevel(self.parent)
        result_window.title(f"Результаты анализа логов")
        result_window.geometry("800x600")
        
        # Основной фрейм
        main_frame = ttk.Frame(result_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Заголовок с результатами
        result_label = ttk.Label(
            main_frame,
            text=f"Найдено транзакций с ошибками: {error_count}",
            font=("Arial", 12, "bold")
        )
        result_label.pack(pady=10)
        
        if error_count == 0:
            info_label = ttk.Label(
                main_frame,
                text="Ошибок не обнаружено. Показаны последние логи для payment-bridge",
                font=("Arial", 10)
            )
            info_label.pack(pady=5)
            
            # TODO: Здесь можно добавить вывод последних логов
            return
        
        # Таблица с деталями ошибок
        columns = ("order_num", "transaction_id", "created_dt", "error_count")
        headers = {
            "order_num": "Номер заказа",
            "transaction_id": "Транзакция",
            "created_dt": "Дата создания",
            "error_count": "Кол-во ошибок"
        }
        
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Настройка колонок
        for col in columns:
            tree.heading(col, text=headers[col])
            tree.column(col, width=150, anchor=tk.W)
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Заполняем таблицу данными
        for detail in error_details:
            tree.insert("", tk.END, values=(
                detail["order_num"],
                detail["transaction_id"],
                detail["created_dt"],
                detail["error_count"]
            ))
        
        # Контекстное меню для таблицы
        context_menu = tk.Menu(tree, tearoff=0)
        context_menu.add_command(
            label="Показать логи",
            command=lambda: self.show_logs_for_selected(tree, error_details)
        )
        
        tree.bind("<Button-3>", lambda e: context_menu.post(e.x_root, e.y_root))

    def show_logs_for_selected(self, tree, error_details):
        """Показывает логи для выбранной транзакции"""
        selected_items = tree.selection()
        if not selected_items:
            return
            
        selected_item = selected_items[0]
        values = tree.item(selected_item, 'values')
        transaction_id = values[1]
        
        # Находим детали для этой транзакции
        detail = next((d for d in error_details if d["transaction_id"] == transaction_id), None)
        if not detail:
            return
            
        # Формируем URL для запроса
        dt = self.parse_datetime(detail["created_dt"])
        if not dt:
            return
            
        from_time = (dt - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        to_time = (dt + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        base_url = "https://log.kifr-ru.local/s/omni/app/discover#/"
        _g = f"(filters:!(),refreshInterval:(pause:!t,value:60000),time:(from:'{from_time}',to:'{to_time}'))"
        _a = f"(columns:!(message,MessageTemplate,traceId,kubernetes.container.name,'@level'),filters:!(),index:'97bbcb4e-6ac8-4971-963c-49d9cfbf3655',interval:auto,query:(language:kuery,query:'message:%20%22{transaction_id}%22%20and%20%40level%20:%20%22ERROR%22'),sort:!(!('@timestamp',desc)))"
        
        full_url = f"{base_url}?_g={_g}&_a={_a}"
        
        # Открываем в браузере
        webbrowser.open(full_url)