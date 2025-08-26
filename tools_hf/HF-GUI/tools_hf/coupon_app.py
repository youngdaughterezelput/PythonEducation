from .base_app import BaseApp
from .database_connector import DatabaseConnector
from .soap_connector import SoapConnector
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from tkcalendar import DateEntry
import xml.etree.ElementTree as ET

class CouponOperationsApp(BaseApp):
    def __init__(self, parent):
        self.db_connector = DatabaseConnector("ORDER")
        self.soap_connector = SoapConnector()
        super().__init__(parent, "Управление купонами")
        
        self.soap_requests = {}
        self.check_db_connection()
        
        self.current_params = None  # Для хранения текущих параметров запроса
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
        
        # Выбор даты через календарь
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
        
        # Кнопки
        self.execute_btn = ttk.Button(
            query_frame,
            text="Выполнить запрос",
            command=self.execute_query
        )
        self.execute_btn.grid(row=0, column=2, padx=10)
        
        ttk.Button(
            query_frame,
            text="Расхолдировать купон",
            command=self.process_coupon
        ).grid(row=0, column=3, padx=10)
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(
            query_frame,
            orient=tk.HORIZONTAL,
            length=200,
            mode='determinate'
        )
        self.progress.grid(row=1, column=0, columnspan=4, pady=5, sticky=tk.EW)
    
    def create_results_section(self):
        results_frame = ttk.LabelFrame(self.window, text="Результаты запроса", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = (
            "requestHoldId", "BU", "POS", "order_num", 
            "coupon", "order_uid", "userId", "created_dt"
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
        
        # Создаем Notebook для вкладок
        self.soap_notebook = ttk.Notebook(soap_frame)
        self.soap_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка с запросами
        self.request_tab = ttk.Frame(self.soap_notebook)
        self.soap_notebook.add(self.request_tab, text="Запросы")
        
        # Вкладка с ответами
        self.response_tab = ttk.Frame(self.soap_notebook)
        self.soap_notebook.add(self.response_tab, text="Ответы")
        
        # Создаем Notebook внутри вкладки ответов
        self.response_notebook = ttk.Notebook(self.response_tab)
        self.response_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка с полным ответом
        self.full_response_frame = ttk.Frame(self.response_notebook)
        self.response_notebook.add(self.full_response_frame, text="Полный ответ")
        
        self.full_response_text = scrolledtext.ScrolledText(
            self.full_response_frame, 
            wrap=tk.WORD, 
            font=('Consolas', 10),
            width=100, 
            height=15
        )
        self.full_response_text.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка с разобранным ответом
        self.parsed_response_frame = ttk.Frame(self.response_notebook)
        self.response_notebook.add(self.parsed_response_frame, text="Разобранный ответ")
        
        # Canvas и Scrollbar для разобранного ответа
        self.parsed_canvas = tk.Canvas(self.parsed_response_frame)
        self.parsed_scrollbar = ttk.Scrollbar(
            self.parsed_response_frame, 
            orient="vertical", 
            command=self.parsed_canvas.yview
        )
        self.parsed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.parsed_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.parsed_canvas.configure(yscrollcommand=self.parsed_scrollbar.set)
        
        # Фрейм для содержимого внутри Canvas
        self.parsed_content_frame = ttk.Frame(self.parsed_canvas)
        self.parsed_canvas.create_window((0, 0), window=self.parsed_content_frame, anchor="nw")
        
        # Привязка события прокрутки
        self.parsed_content_frame.bind(
            "<Configure>",
            lambda e: self.parsed_canvas.configure(
                scrollregion=self.parsed_canvas.bbox("all")
            )
        )
    
    def execute_query(self):
        if self.query_in_progress:
            messagebox.showwarning("Предупреждение", "Запрос уже выполняется")
            return

        try:
            self.query_in_progress = True
            self.execute_btn.config(state=tk.DISABLED)
            self.progress['value'] = 10
            self.window.update()

            # Получаем выбранную дату
            selected_date = self.date_entry.get_date()
            current_params = selected_date

            # Проверяем, изменились ли параметры
            if self.current_params == current_params and hasattr(self, 'data'):
                if messagebox.askyesno("Подтверждение", 
                                    "Параметры не изменились. Повторить запрос с теми же параметрами?"):
                    self._run_query_with_progress(selected_date)
                return
            else:
                self.current_params = current_params
                self._run_query_with_progress(selected_date)

        except Exception as e:
            import traceback
            error_msg = f"Ошибка выполнения запроса: {str(e)}\n{traceback.format_exc()}"
            messagebox.showerror("Ошибка", error_msg)
            print(error_msg)  # Логируем ошибку в консоль
        finally:
            self.query_in_progress = False
            self.execute_btn.config(state=tk.NORMAL)
            self.progress['value'] = 0

    def _run_query_with_progress(self, selected_date):
        """Вспомогательный метод для выполнения запроса с прогресс-баром"""
        try:
            self.progress['value'] = 20
            self.window.update()

            # Форматируем дату для SQL запроса
            date_str = selected_date.strftime('%Y-%m-%d')

            query = """
            SELECT
                (order_json -> 'coupon' -> 0 ->> 'requestHoldId') as requestHoldId,
                (order_json ->> 'businessUnitId') as BU,
                (order_json -> 'coupon' -> 0 ->> 'POS') as POS,
                order_num,
                (order_json -> 'coupon' -> 0 ->> 'coupon') as coupon,
                order_uid,
                (order_json ->> 'userId') as userId,
                created_dt
            FROM ordercmp."order" o
            WHERE (o.order_status_id = 'EXPIRED' OR o.order_status_id = 'NEW')
            AND o.order_json::varchar LIKE '%%coupon%%'
            AND o.order_json::varchar NOT LIKE '%%tyta100%%'
            AND created_dt::date = %s
            ORDER BY created_dt DESC;
            """

            self.progress['value'] = 40
            self.window.update()

            # Выполняем запрос с параметром даты
            self.data = self.db_connector.execute_query(query, (date_str,))

            self.progress['value'] = 70
            self.window.update()

            # Очищаем предыдущие результаты
            self.results_tree.delete(*self.results_tree.get_children())

            # Проверяем наличие данных
            if not self.data:
                messagebox.showinfo("Информация", "По указанным параметрам данные не найдены")
                return

            # Добавляем данные в Treeview с проверкой
            for row in self.data:
                try:
                    # Преобразуем в список и дополняем None при необходимости
                    row_values = list(row)
                    while len(row_values) < 8:  # 8 - количество ожидаемых колонок
                        row_values.append(None)
                    self.results_tree.insert("", tk.END, values=row_values)
                except Exception as e:
                    import traceback
                    print(f"Ошибка при добавлении строки: {row}\n{traceback.format_exc()}")
                    continue

            self.progress['value'] = 100
            messagebox.showinfo("Успех", f"Найдено записей: {len(self.data)}")

        except Exception as e:
            import traceback
            error_msg = f"Ошибка при выполнении запроса:\n{str(e)}\n{traceback.format_exc()}"
            messagebox.showerror("Ошибка запроса", error_msg)
            print(error_msg)
    
    def generate_soap(self):
        selected_items = self.results_tree.selection()
        if not selected_items:
            messagebox.showinfo("Информация", "Выберите записи для генерации SOAP")
            return
        
        # Очищаем предыдущие запросы
        for widget in self.request_tab.winfo_children():
            widget.destroy()
        
        # Создаем Notebook для запросов
        self.request_notebook = ttk.Notebook(self.request_tab)
        self.request_notebook.pack(fill=tk.BOTH, expand=True)
        
        self.soap_requests = {}
        
        for item in selected_items:
            values = self.results_tree.item(item, "values")
            if not values or len(values) < 8:
                continue
            
            requestHoldId = values[0]
            BU = values[1]
            POS = values[2]
            order_num = values[3]
            coupon = values[4]
            created_dt = values[7]
            
            current_time = self.soap_connector.format_datetime(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'))
            ref_datetime = self.soap_connector.format_datetime(created_dt)
            
            request_id = f"{requestHoldId}"
            
            soap_template = f"""
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:loy="http://loyalty.manzanagroup.ru/loyalty.xsd">
    <soap:Header/>
    <soap:Body>
        <loy:ProcessRequest>
            <loy:request>
                <loy:ChequeRequest ChequeType="Soft">
                    <loy:RequestID>{request_id}</loy:RequestID>
                    <loy:Card>
                        <loy:CardNumber>Hoff0</loy:CardNumber>
                    </loy:Card>
                    <loy:DateTime>{current_time}</loy:DateTime>
                    <loy:Organization>hoff</loy:Organization>
                    <loy:BusinessUnit>{BU}s</loy:BusinessUnit>
                    <loy:POS>{POS}</loy:POS>
                    <loy:Number>{request_id}</loy:Number>
                    <loy:OperationType>Sale</loy:OperationType>
                    <loy:ExtendedAttribute>
                        <loy:Key>ordernum</loy:Key>
                        <loy:Value>{order_num}</loy:Value>
                    </loy:ExtendedAttribute>
                    <loy:Coupons>
                        <loy:Coupon>
                            <loy:Number>{coupon}</loy:Number>
                            <loy:ExtendedAttribute>
                                <loy:Key>freez</loy:Key>
                                <loy:Value>2</loy:Value>
                            </loy:ExtendedAttribute>
                        </loy:Coupon>
                    </loy:Coupons>
                </loy:ChequeRequest>
            </loy:request>
            <loy:orgName>hoff</loy:orgName>
        </loy:ProcessRequest>
    </soap:Body>
</soap:Envelope>
            """
            
            self.soap_requests[item] = {
                'soap': soap_template,
                'request_id': request_id
            }
            
            # Добавляем вкладку с запросом
            frame = ttk.Frame(self.request_notebook)
            text_area = scrolledtext.ScrolledText(frame, width=100, height=15)
            text_area.pack(fill=tk.BOTH, expand=True)
            text_area.insert(tk.END, soap_template)
            text_area.config(state=tk.DISABLED)
            
            self.request_notebook.add(frame, text=f"Запрос {request_id}")
    
    def process_coupon(self):
        if not self.soap_requests:
            messagebox.showinfo("Информация", "Нет сгенерированных запросов")
            return
        
        if not self.soap_connector.check_auth():
            self.soap_connector.show_auth_dialog(self.window, self._process_coupon_requests)
            return
        
        self._process_coupon_requests()
    
    def _process_coupon_requests(self):
        self.results = {}
        
        # Очищаем предыдущие ответы
        for widget in self.full_response_frame.winfo_children():
            widget.destroy()
        for widget in self.parsed_content_frame.winfo_children():
            widget.destroy()
        
        # Переключаемся на вкладку ответов
        self.soap_notebook.select(self.response_tab)
        
        for item_id, soap_data in self.soap_requests.items():
            result = self.soap_connector.send_request(soap_data['soap'])
            result['request_id'] = soap_data['request_id']
            self.results[item_id] = result
            
            # Обновляем Treeview с результатами
            values = list(self.results_tree.item(item_id, "values"))
            
            # Парсим XML ответ для получения ApplicabilityMessage
            applicability_message = self._parse_applicability_message(result['response'])
            
            # Добавляем статус и сообщение в конец строки
            self.results_tree.item(item_id, values=values + [result['status'], applicability_message])
            
            # Обновляем вкладку с полным ответом
            self._update_response_tabs(result)
        
        messagebox.showinfo("Готово", "Обработка запросов завершена")
    
    def _parse_applicability_message(self, xml_response):
        """Извлекает сообщение ApplicabilityMessage из XML ответа"""
        try:
            root = ET.fromstring(xml_response)
            ns = {'soap': 'http://www.w3.org/2003/05/soap-envelope',
                  'loy': 'http://loyalty.manzanagroup.ru/loyalty.xsd'}
            
            # Ищем ApplicabilityMessage в ответе
            applicability = root.find('.//loy:ApplicabilityMessage', ns)
            if applicability is not None:
                return applicability.text
        except Exception as e:
            print(f"Ошибка при парсинге XML: {str(e)}")
        return "N/A"
    
    def _update_response_tabs(self, result):
        """Обновляет вкладки с ответами"""
        # Обновляем полный ответ
        self.full_response_text = scrolledtext.ScrolledText(
            self.full_response_frame, 
            wrap=tk.WORD, 
            font=('Consolas', 10),
            width=100, 
            height=15
        )
        self.full_response_text.pack(fill=tk.BOTH, expand=True)
        self.full_response_text.insert(tk.END, f"Статус: {result['status']}\n")
        self.full_response_text.insert(tk.END, f"Ответ сервера:\n{result['response']}")
        self.full_response_text.config(state=tk.DISABLED)
        
        # Парсим XML и обновляем разобранный ответ
        try:
            root = ET.fromstring(result['response'])
            ns = {'soap': 'http://www.w3.org/2003/05/soap-envelope',
                  'loy': 'http://loyalty.manzanagroup.ru/loyalty.xsd'}
            
            # Очищаем предыдущие фреймы
            for widget in self.parsed_content_frame.winfo_children():
                widget.destroy()
            
            row = 0
            
            # Общая информация
            status_frame = ttk.LabelFrame(
                self.parsed_content_frame, 
                text="Статус выполнения", 
                padding="5"
            )
            status_frame.grid(row=row, column=0, sticky=tk.W+tk.E, pady=5, padx=5)
            row += 1
            
            ttk.Label(status_frame, text="Статус:", font=('Arial', 9, 'bold')).grid(
                sticky=tk.W, padx=5, pady=2)
            ttk.Label(status_frame, text=result['status']).grid(
                sticky=tk.W, padx=15, pady=2)
            
            # Сообщения
            messages = root.findall('.//loy:Message', ns)
            if messages:
                messages_frame = ttk.LabelFrame(
                    self.parsed_content_frame, 
                    text="Сообщения", 
                    padding="5"
                )
                messages_frame.grid(row=row, column=0, sticky=tk.W+tk.E, pady=5, padx=5)
                row += 1
                
                for i, msg in enumerate(messages):
                    ttk.Label(messages_frame, text=f"Сообщение {i+1}:", font=('Arial', 9, 'bold')).grid(
                        sticky=tk.W, padx=5, pady=2)
                    ttk.Label(messages_frame, text=msg.text).grid(
                        sticky=tk.W, padx=15, pady=2)
            
            # ApplicabilityMessage
            applicability = root.find('.//loy:ApplicabilityMessage', ns)
            if applicability is not None:
                applicability_frame = ttk.LabelFrame(
                    self.parsed_content_frame, 
                    text="Applicability Message", 
                    padding="5"
                )
                applicability_frame.grid(row=row, column=0, sticky=tk.W+tk.E, pady=5, padx=5)
                row += 1
                
                ttk.Label(applicability_frame, text="Сообщение:").grid(
                    sticky=tk.W, padx=5, pady=2)
                ttk.Label(applicability_frame, text=applicability.text).grid(
                    sticky=tk.W, padx=15, pady=2)
            
            # Обновляем canvas
            self.parsed_content_frame.update_idletasks()
            self.parsed_canvas.config(scrollregion=self.parsed_canvas.bbox("all"))
            
        except Exception as e:
            print(f"Ошибка при парсинге XML ответа: {str(e)}")
    
    def _prepare_export_row(self, values):
        return {
            "requestHoldId": values[0],
            "BU": values[1],
            "POS": values[2],
            "order_num": values[3],
            "coupon": values[4],
            "order_uid": values[5],
            "userId": values[6],
            "created_dt": values[7],
            "Статус": values[8] if len(values) > 8 else "N/A",
            "ApplicabilityMessage": values[9] if len(values) > 9 else "N/A"
        }