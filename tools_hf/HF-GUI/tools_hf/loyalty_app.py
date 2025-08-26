from .base_app import BaseApp
from .database_connector import DatabaseConnector
from .soap_connector import SoapConnector
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from tkcalendar import DateEntry  # Импорт календаря

class LoyaltyOperationsApp(BaseApp):
    def __init__(self, parent):
        self.db_connector = DatabaseConnector("ORDER")
        self.soap_connector = SoapConnector()
        super().__init__(parent, "Управление холдами лояльности")
        
        self.soap_requests = {}
        self.check_db_connection()

        self.current_params = None  # Добавляем для хранения текущих параметров
        self.query_in_progress = False  # Флаг выполнения запроса
    
    def create_db_connection_section(self):
        super().create_db_connection_section()
    
    def check_db_connection(self):
        if self.db_connector.check_connection(self.window):
            self.db_status.config(text="Статус БД: Подключено")
        else:
            self.db_status.config(text="Статус БД: Ошибка подключения")

    def setup_context_menu(self):
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
        self.soap_context_menu.post(event.x_root, event.y_root)
    
    def create_query_section(self):
        query_frame = ttk.LabelFrame(self.window, text="Параметры запроса", padding=10)
        query_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Фиксированный статус заказа
        ttk.Label(query_frame, text="Статус заказа:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(query_frame, text="EXPIRED").grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Выбор даты через календарь
        ttk.Label(query_frame, text="Дата:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.date_entry = DateEntry(
            query_frame,
            date_pattern='yyyy-mm-dd',
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2
        )
        self.date_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Кнопки
        self.execute_btn = ttk.Button(
            query_frame,
            text="Выполнить запрос",
            command=self.execute_query
        )
        self.execute_btn.grid(row=0, column=4, padx=10)
        
        ttk.Button(
            query_frame,
            text="Расхолдировать",
            command=self.process_hold
        ).grid(row=0, column=5, padx=10)
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(
            query_frame,
            orient=tk.HORIZONTAL,
            length=200,
            mode='determinate'
        )
        self.progress.grid(row=1, column=0, columnspan=6, pady=5, sticky=tk.EW)
    
    def create_results_section(self):
        results_frame = ttk.LabelFrame(self.window, text="Результаты запроса", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = (
            "requestHoldId", "loyaltyCardId", "order_num", "loyaltyWriteOff",
            "BU", "POS", "order_uid", "userId", "created_dt"
        )
        
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
        if self.query_in_progress:
            messagebox.showwarning("Предупреждение", "Запрос уже выполняется")
            return

        try:
            self.query_in_progress = True
            self.execute_btn.config(state=tk.DISABLED)
            self.progress['value'] = 10
            self.window.update()

            # Получаем текущие параметры
            status = "EXPIRED"  # Фиксированный статус
            selected_date = self.date_entry.get_date()
            current_params = (status, selected_date)

            # Проверяем, изменились ли параметры
            if self.current_params == current_params and hasattr(self, 'data'):
                if messagebox.askyesno("Подтверждение", 
                                    "Параметры не изменились. Повторить запрос с теми же параметрами?"):
                    self._run_query_with_progress(status, selected_date)
                return
            else:
                self.current_params = current_params
                self._run_query_with_progress(status, selected_date)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка выполнения запроса: {str(e)}")
        finally:
            self.query_in_progress = False
            self.execute_btn.config(state=tk.NORMAL)
            self.progress['value'] = 0

    def _run_query_with_progress(self, status, selected_date):
        """Вспомогательный метод для выполнения запроса с прогресс-баром"""
        try:
            self.progress['value'] = 20
            self.window.update()

            # Формируем условие для даты (точное совпадение с выбранной датой)
            date_str = selected_date.strftime('%Y-%m-%d')
            date_condition = "AND o.created_dt::date = %s"

            query = f"""
            SELECT
                order_json -> 'loyaltyCard'->>'requestHoldId' as requestHoldId,
                order_json -> 'loyaltyCard'->>'loyaltyCardId' as loyaltyCardId,
                order_num,
                order_json -> 'loyaltyCard'->>'loyaltyWriteOff' as loyaltyWriteOff,
                order_json ->> 'businessUnitId' as BU,
                order_json -> 'loyaltyCard'->>'POS' as POS,
                order_uid,
                order_json->>'userId' as userId,
                created_dt::timestamp
            FROM ordercmp."order" o
            WHERE o.order_status_id = %s
            AND o.order_json::varchar LIKE '%%loyaltyWriteOff%%'
            AND o.order_json::varchar NOT LIKE '%%loyaltyWriteOff": 0%%'
            {date_condition}
            ORDER BY created_dt DESC;
            """

            self.progress['value'] = 40
            self.window.update()

            # Выполняем запрос с параметрами
            self.data = self.db_connector.execute_query(query, (status, date_str))

            self.progress['value'] = 70
            self.window.update()

            # Обновляем Treeview
            self.results_tree.delete(*self.results_tree.get_children())
            for row in self.data:
                self.results_tree.insert("", tk.END, values=row)

            self.progress['value'] = 100
            messagebox.showinfo("Успех", f"Найдено записей: {len(self.data)}")

        except Exception as e:
            messagebox.showerror("Ошибка запроса", f"Ошибка при выполнении запроса:\n{str(e)}")
            raise
    
    # Остальные методы остаются без изменений
    def generate_soap(self):
        selected_items = self.results_tree.selection()
        if not selected_items:
            messagebox.showinfo("Информация", "Выберите записи для генерации SOAP")
            return
        
        for tab_id in self.soap_notebook.tabs()[1:]:
            self.soap_notebook.forget(tab_id)
        
        self.soap_requests = {}
        
        for item in selected_items:
            values = self.results_tree.item(item, "values")
            if not values or len(values) < 9:
                continue
            
            requestHoldId = values[0]
            loyaltyCardId = values[1]
            order_num = values[2]
            BU = values[4]
            POS = values[5]
            created_dt_str = values[8]
            
            # Исправленный блок парсинга даты
            try:
                if '.' in created_dt_str and '+' in created_dt_str:
                    main_part, tz_part = created_dt_str.split('+')
                    date_part, fractional = main_part.split('.')
                    fractional = fractional[:6]
                    normalized_str = f"{date_part}.{fractional}+{tz_part}"
                    created_dt = datetime.strptime(normalized_str, '%Y-%m-%d %H:%M:%S.%f%z')
                else:
                    formats = [
                        '%Y-%m-%d %H:%M:%S.%f%z',
                        '%Y-%m-%d %H:%M:%S%z',
                        '%Y-%m-%d %H:%M:%S.%f',
                        '%Y-%m-%d %H:%M:%S'
                    ]
                    for fmt in formats:
                        try:
                            created_dt = datetime.strptime(created_dt_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        created_dt = datetime.now()
            except Exception:
                created_dt = datetime.now()
            
            # Форматирование даты (должно быть внутри цикла!)
            ref_datetime = self.soap_connector.format_datetime(created_dt)
            cur_datetime = self.soap_connector.format_datetime(datetime.now())
            
            last_four = order_num[-4:] if len(order_num) >= 4 else "0000"
            request_id = f"{last_four}{requestHoldId}"
            
            # Генерация SOAP-шаблона
            soap_template = f"""
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
            xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <ProcessRequest xmlns="http://loyalty.manzanagroup.ru/loyalty.xsd">
            <request>
                <BonusRequest>
                    <RequestID>{request_id}</RequestID>
                    <DateTime>{cur_datetime}</DateTime>
                    <Organization>hoff</Organization>
                    <BusinessUnit>{BU}s</BusinessUnit>
                    <POS>{POS}</POS>
                    <Number>{requestHoldId}</Number>
                    <OperationType>Return</OperationType>
                    <Card>
                        <CardNumber>{loyaltyCardId}</CardNumber>
                    </Card>
                    <RequestReference>
                        <Number>{requestHoldId}</Number>
                        <POS>{POS}</POS>
                        <DateTime>{ref_datetime}</DateTime>
                        <BusinessUnit>{BU}s</BusinessUnit>
                        <Organization>hoff</Organization>
                    </RequestReference>
                </BonusRequest>
            </request>
            <orgName>hoff</orgName>
        </ProcessRequest>
    </s:Body>
</s:Envelope>
            """.strip()
            
            self.soap_requests[item] = {
                'soap': soap_template,
                'request_id': request_id
            }
            
            frame = ttk.Frame(self.soap_notebook)
            text_area = scrolledtext.ScrolledText(frame, width=100, height=15)
            text_area.pack(fill=tk.BOTH, expand=True)
            text_area.insert(tk.END, soap_template)
            text_area.config(state=tk.DISABLED)
            
            self.soap_notebook.add(frame, text=f"Запрос {request_id}")
    
    def process_hold(self):
        if not self.soap_requests:
            messagebox.showinfo("Информация", "Нет сгенерированных запросов")
            return
        
        if not self.soap_connector.check_auth():
            self.soap_connector.show_auth_dialog(self.window, self._process_hold_requests)
            return
        
        self._process_hold_requests()
    
    def _process_hold_requests(self):
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
    
    def _prepare_export_row(self, values):
        return {
            "requestHoldId": values[0],
            "loyaltyCardId": values[1],
            "order_num": values[2],
            "loyaltyWriteOff": values[3],
            "BU": values[4],
            "POS": values[5],
            "order_uid": values[6],
            "userId": values[7],
            "created_dt": values[8],
            "Статус": values[9] if len(values) > 9 else "N/A"
        }