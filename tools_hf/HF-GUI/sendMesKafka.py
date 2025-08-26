import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from confluent_kafka import Producer, Consumer, OFFSET_BEGINNING
from confluent_kafka.admin import NewTopic, AdminClient
import json
import socket
from datetime import datetime
import threading
import requests
from requests.auth import HTTPBasicAuth
import re
import urllib3
from bs4 import BeautifulSoup
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Отключаем предупреждения о небезопасных запросах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class KafkaProducerApp:
    def __init__(self, parent=None):
        # Создаем собственное окно, если не передано родительское
        if parent is None:
            self.parent = tk.Tk()
            self.is_root = True
        else:
            self.parent = parent
            self.is_root = False

        self.parent.title("Kafka Send")
        self.history = []
        self.history_limit = 100
        self.dlq_messages = []
        self.ui_data = []
        self.cluster_name = "default"  # Имя кластера по умолчанию
        self.session = requests.Session()  # Сессия для сохранения cookies
        
        # Настройки по умолчанию
        self.default_config = {
            'bootstrap_servers': 'localhost:9092',
            'topic_name': 'test-topic',
            'security_protocol': 'PLAINTEXT',
            'ssl_ca_location': '',
            'sasl_mechanism': 'PLAIN',
            'sasl_username': '',
            'sasl_password': '',
            'kafka_ui_url': 'https://omni-kafkaui.kifr-ru.local/',
            'kafka_ui_user': '',
            'kafka_ui_pass': ''
        }

        # Добавляем новую переменную для хранения выбранного сообщения
        self.selected_message = None
        
        self.create_widgets()

        # Запускаем mainloop только если это корневое окно
        if self.is_root:
            self.parent.mainloop()

        # Кэширование данных
        self.cache = {
            'topics': {'data': [], 'timestamp': None},
            'brokers': {'data': [], 'timestamp': None},
            'consumers': {'data': [], 'timestamp': None}
        }
        self.cache_timeout = 300  # 5 минут кэширования
        self.loading_canceled = False
        
    def create_widgets(self):
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill='both', expand=True)
        
        # Вкладка основной конфигурации
        main_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text='Main')
        
        # Фрейм сообщения
        message_frame = ttk.LabelFrame(main_tab, text="Message", padding=15)
        message_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Новая строка с полями Partition и Headers
        ttk.Label(message_frame, text="Partition:").grid(row=0, column=0, sticky='w')
        self.partition_entry = ttk.Entry(message_frame, width=10)
        self.partition_entry.grid(row=0, column=1, sticky='w', padx=5, pady=2)

        ttk.Label(message_frame, text="Headers (key:value):").grid(row=0, column=2, sticky='w')
        self.headers_entry = ttk.Entry(message_frame)
        self.headers_entry.grid(row=0, column=3, sticky='ew', padx=5, pady=2)
        
        # Key
        ttk.Label(message_frame, text="Key:").grid(row=1, column=0, sticky='w')
        self.key_entry = ttk.Entry(message_frame)
        self.key_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        # JSON validation
        self.json_check = tk.BooleanVar()
        self.json_checkbox = ttk.Checkbutton(message_frame, text="Validate JSON", variable=self.json_check)
        self.json_checkbox.grid(row=1, column=2, padx=5)
        
        # Message editor
        self.message_editor = scrolledtext.ScrolledText(message_frame, height=10)
        self.message_editor.grid(row=2, column=0, columnspan=4, sticky='nsew', pady=5)

        # Кнопки сообщений
        btn_frame = ttk.Frame(message_frame)
        btn_frame.grid(row=3, column=0, columnspan=4, sticky='e')
        
        self.format_json_btn = ttk.Button(btn_frame, text="Format JSON", command=self.format_json)
        self.format_json_btn.pack(side='right', padx=2)
        
        self.send_btn = ttk.Button(btn_frame, text="Send Message", command=self.send_message)
        self.send_btn.pack(side='right', padx=2)
        
        # Фрейм DLQ сообщений
        dlq_frame = ttk.LabelFrame(main_tab, text="DLQ Messages", padding=10)
        dlq_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Выбор топика DLQ
        ttk.Label(dlq_frame, text="DLQ Topic:").grid(row=0, column=0, sticky='w')
        self.dlq_topic_combobox = ttk.Combobox(dlq_frame, state="readonly")
        self.dlq_topic_combobox.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        self.dlq_topic_combobox.bind('<<ComboboxSelected>>', self.on_dlq_topic_selected)
        
        # Кнопки для DLQ
        dlq_btn_frame = ttk.Frame(dlq_frame)
        dlq_btn_frame.grid(row=0, column=2, columnspan=2, sticky='e')
        
        self.refresh_dlq_btn = ttk.Button(dlq_btn_frame, text="🔄", width=3, command=self.load_dlq_topics)
        self.refresh_dlq_btn.pack(side='left', padx=2)
        
        self.load_dlq_btn = ttk.Button(dlq_btn_frame, text="Load Messages", command=self.start_dlq_loading)
        self.load_dlq_btn.pack(side='left', padx=2)
        
        # Treeview для DLQ
        columns = ('partition', 'offset', 'key', 'value', 'timestamp')
        self.dlq_tree = ttk.Treeview(dlq_frame, columns=columns, show='headings')
        
        self.dlq_tree.heading('partition', text='Partition')
        self.dlq_tree.heading('offset', text='Offset')
        self.dlq_tree.heading('key', text='Key')
        self.dlq_tree.heading('value', text='Value')
        self.dlq_tree.heading('timestamp', text='Timestamp')
        
        self.dlq_tree.column('partition', width=70)
        self.dlq_tree.column('offset', width=70)
        self.dlq_tree.column('key', width=100)
        self.dlq_tree.column('value', width=300)
        self.dlq_tree.column('timestamp', width=120)
        
        scrollbar = ttk.Scrollbar(dlq_frame, orient="vertical", command=self.dlq_tree.yview)
        self.dlq_tree.configure(yscrollcommand=scrollbar.set)
        
        self.dlq_tree.grid(row=1, column=0, columnspan=3, sticky='nsew', pady=5)
        scrollbar.grid(row=1, column=3, sticky='ns')

        self.dlq_tree.bind("<Button-3>", self.show_message_context_menu)
        
        # Вкладка настроек
        settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(settings_tab, text='Settings')
        
        # Фрейм подключения Kafka
        connection_frame = ttk.LabelFrame(settings_tab, text="Kafka Connection Settings", padding=10)
        connection_frame.pack(fill='x', padx=10, pady=5)

        test_kafka_btn = ttk.Button(connection_frame, text="Test Connection", command=self.test_kafka_connection)
        #ttk.Button(connection_frame, text="Test Connection", command=self.test_kafka_ui_connection)
        test_kafka_btn.grid(row=2, column=1, sticky='e', pady=5)
        
        # Bootstrap servers
        ttk.Label(connection_frame, text="Bootstrap Servers:").grid(row=0, column=0, sticky='w')
        self.bootstrap_entry = ttk.Entry(connection_frame)
        self.bootstrap_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        self.bootstrap_entry.insert(0, self.default_config['bootstrap_servers'])
        
        # Выбор топика
        ttk.Label(connection_frame, text="Topic:").grid(row=1, column=0, sticky='w')
        self.topic_combobox = ttk.Combobox(connection_frame)
        self.topic_combobox.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        self.refresh_topics_btn = ttk.Button(connection_frame, text="🔄", width=3, command=self.load_topics)
        self.refresh_topics_btn.grid(row=1, column=2, padx=2)
        
        # Фрейм безопасности Kafka
        security_frame = ttk.LabelFrame(settings_tab, text="Kafka Security Settings", padding=10)
        security_frame.pack(fill='x', padx=10, pady=5)
        
        # Security protocol
        ttk.Label(security_frame, text="Protocol:").grid(row=0, column=0, sticky='w')
        self.security_protocol = ttk.Combobox(security_frame, values=['PLAINTEXT', 'SSL', 'SASL_PLAIN', 'SASL_SSL'])
        self.security_protocol.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        self.security_protocol.set(self.default_config['security_protocol'])
        self.security_protocol.bind('<<ComboboxSelected>>', self.update_security_fields)
        
        # SSL CA location
        ttk.Label(security_frame, text="SSL CA Path:").grid(row=1, column=0, sticky='w')
        self.ssl_ca_entry = ttk.Entry(security_frame)
        self.ssl_ca_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        # SASL credentials
        ttk.Label(security_frame, text="Username:").grid(row=2, column=0, sticky='w')
        self.sasl_user_entry = ttk.Entry(security_frame)
        self.sasl_user_entry.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(security_frame, text="Password:").grid(row=3, column=0, sticky='w')
        self.sasl_pass_entry = ttk.Entry(security_frame, show='*')
        self.sasl_pass_entry.grid(row=3, column=1, sticky='ew', padx=5, pady=2)
        
        # Фрейм Kafka UI
        ui_frame = ttk.LabelFrame(settings_tab, text="Kafka UI Settings", padding=10)
        ui_frame.pack(fill='x', padx=10, pady=5)
        
        # Kafka UI URL
        ttk.Label(ui_frame, text="Kafka UI URL:").grid(row=0, column=0, sticky='w')
        self.kafka_ui_url_entry = ttk.Entry(ui_frame)
        self.kafka_ui_url_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        self.kafka_ui_url_entry.insert(0, self.default_config['kafka_ui_url'])
        
        # Kafka UI credentials
        ttk.Label(ui_frame, text="Username:").grid(row=1, column=0, sticky='w')
        self.kafka_ui_user_entry = ttk.Entry(ui_frame)
        self.kafka_ui_user_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        ttk.Label(ui_frame, text="Password:").grid(row=2, column=0, sticky='w')
        self.kafka_ui_pass_entry = ttk.Entry(ui_frame, show='*')
        self.kafka_ui_pass_entry.grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        
        # Кнопка проверки подключения к Kafka UI
        test_btn = ttk.Button(ui_frame, text="Test Connection", command=self.test_kafka_ui_connection)
        test_btn.grid(row=3, column=1, sticky='e', pady=5)
        
        # Вкладка Kafka UI Data
        ui_data_tab = ttk.Frame(self.notebook)
        self.notebook.add(ui_data_tab, text='Kafka UI Data')
        
        # Фрейм данных Kafka UI
        ui_data_frame = ttk.LabelFrame(ui_data_tab, text="Data from Kafka UI", padding=10)
        ui_data_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # В фрейме данных Kafka UI
        ttk.Label(ui_data_frame, text="Data Type:").grid(row=0, column=0, sticky='w')
        self.data_type_combobox = ttk.Combobox(ui_data_frame, values=['Topics', 'Brokers', 'Consumers'])
        self.data_type_combobox.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        self.data_type_combobox.set('Topics')
        
        # Кнопка загрузки данных
        self.load_data_btn = ttk.Button(ui_data_frame, text="Load Data", command=self.load_kafka_ui_data)
        self.load_data_btn.grid(row=0, column=2, sticky='e', padx=5, pady=2)
        
        # Кнопка отмены
        self.cancel_btn = ttk.Button(ui_data_frame, text="Cancel", 
                                    command=self.cancel_loading, state=tk.DISABLED)
        self.cancel_btn.grid(row=0, column=3, sticky='e', padx=5, pady=2)
        
        # ДОБАВЛЕНО: Переключатель фильтрации DLQ
        self.filter_dlq = tk.BooleanVar(value=True)
        self.filter_check = ttk.Checkbutton(
            ui_data_frame, 
            text="Filter DLQ topics", 
            variable=self.filter_dlq,
            command=self.toggle_dlq_filter
        )
        self.filter_check.grid(row=0, column=2, padx=5, sticky='w')
        
        # Кнопка загрузки данных
        load_data_btn = ttk.Button(ui_data_frame, text="Load Data", command=self.load_kafka_ui_data)
        load_data_btn.grid(row=0, column=3, sticky='e', padx=5, pady=2)
        
        # Treeview для данных Kafka UI
        columns = ('name', 'type', 'details')
        self.ui_data_tree = ttk.Treeview(ui_data_frame, columns=columns, show='headings')
        
        self.ui_data_tree.heading('name', text='Name')
        self.ui_data_tree.heading('type', text='Type')
        self.ui_data_tree.heading('details', text='Details')
        
        self.ui_data_tree.column('name', width=150)
        self.ui_data_tree.column('type', width=100)
        self.ui_data_tree.column('details', width=300)
        
        scrollbar = ttk.Scrollbar(ui_data_frame, orient="vertical", command=self.ui_data_tree.yview)
        self.ui_data_tree.configure(yscrollcommand=scrollbar.set)
        
        self.ui_data_tree.grid(row=1, column=0, columnspan=3, sticky='nsew', pady=5)
        scrollbar.grid(row=1, column=3, sticky='ns')
        self.ui_data_tree.bind("<Button-3>", self.show_topic_context_menu)
        
        # Вкладка истории
        history_tab = ttk.Frame(self.notebook)
        self.notebook.add(history_tab, text='History')
        
        # История сообщений
        columns = ('time', 'topic', 'key', 'message')
        self.history_tree = ttk.Treeview(history_tab, columns=columns, show='headings')
        
        self.history_tree.heading('time', text='Time')
        self.history_tree.heading('topic', text='Topic')
        self.history_tree.heading('key', text='Key')
        self.history_tree.heading('message', text='Message')
        
        self.history_tree.column('time', width=120)
        self.history_tree.column('topic', width=100)
        self.history_tree.column('key', width=80)
        self.history_tree.column('message', width=300)
        
        self.history_tree.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Кнопка очистки истории
        clear_btn = ttk.Button(history_tab, text="Clear History", command=self.clear_history)
        clear_btn.pack(side='right', padx=10, pady=5)
        
        # Настройка весов строк и колонок
        main_tab.columnconfigure(0, weight=1)
        message_frame.columnconfigure(1, weight=1)
        message_frame.rowconfigure(1, weight=1)
        dlq_frame.rowconfigure(1, weight=1)
        dlq_frame.columnconfigure(1, weight=1)
        ui_data_frame.rowconfigure(1, weight=1)
        ui_data_frame.columnconfigure(1, weight=1)
        
        # Инициализация полей безопасности
        self.update_security_fields()

    # Метод для обновления состояния фильтра
    def toggle_dlq_filter(self):
        """Переключает фильтр DLQ"""
        # Фильтр применяется только к топикам
        if self.data_type_combobox.get().lower() == 'topics':
            self.load_kafka_ui_data()

    def on_dlq_topic_selected(self, event):
        """Автоматическая загрузка сообщений при выборе топика"""
        self.start_dlq_loading()

    def kafka_ui_login(self, url, username, password):
        """Выполняет вход в Kafka UI через Keycloak с использованием BeautifulSoup"""
        try:
            # Нормализуем URL
            url = url.rstrip('/') + '/'
            
            # Получаем страницу входа
            login_page = self.session.get(url, verify=False, timeout=10)
            
            # Если нас перенаправили на другую страницу (уже аутентифицированы)
            if "login" not in login_page.url.lower() and "auth" not in login_page.url.lower():
                return True
                
            # Используем BeautifulSoup для парсинга HTML
            soup = BeautifulSoup(login_page.text, 'html.parser')
            
            # Ищем ссылку для входа через Keycloak
            keycloak_link = None
            for link in soup.find_all('a'):
                href = link.get('href', '').lower()
                if 'keycloak' in href or 'sso' in href or 'auth' in href:
                    keycloak_link = link.get('href')
                    break
                    
            if keycloak_link:
                # Обработка Keycloak
                return self.handle_keycloak_login(keycloak_link, login_page.url, username, password)
                
            # Проверяем, есть ли прямая форма входа
            login_form = soup.find('form')
            if login_form:
                # Проверяем наличие полей username/password
                username_field = login_form.find(attrs={'name': re.compile(r'user(name)?|login|email', re.I)})
                password_field = login_form.find(attrs={'type': 'password'})
                
                if username_field and password_field:
                    return self.handle_direct_login(login_form, login_page.url, username, password)
            
            # Если ничего не найдено
            raise Exception("No login form detected. Check if authentication method changed.")
            
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")

    # Новый метод для обработки Keycloak
    def handle_keycloak_login(self, keycloak_link, base_url, username, password):
        """Обрабатывает вход через Keycloak"""
        # Обрабатываем относительные URL
        if keycloak_link.startswith('/'):
            base_domain = '/'.join(base_url.split('/')[:3])
            keycloak_url = base_domain + keycloak_link
        else:
            keycloak_url = keycloak_link
            
        # Получаем страницу аутентификации Keycloak
        auth_page = self.session.get(keycloak_url, verify=False, timeout=10)
        auth_soup = BeautifulSoup(auth_page.text, 'html.parser')
        
        # Находим форму входа
        login_form = auth_soup.find('form')
        if not login_form:
            raise Exception("Login form not found on Keycloak page")
            
        # Извлекаем параметры формы
        form_action = login_form.get('action')
        if not form_action:
            raise Exception("Form action not found")
            
        # Собираем скрытые поля
        form_data = {}
        for hidden_input in login_form.find_all('input', type='hidden'):
            name = hidden_input.get('name')
            value = hidden_input.get('value')
            if name and value:
                form_data[name] = value
                
        # Добавляем учетные данные
        form_data['username'] = username
        form_data['password'] = password
        
        # Отправляем форму входа
        if form_action.startswith('/'):
            form_action = '/'.join(keycloak_url.split('/')[:3]) + form_action
            
        response = self.session.post(
            form_action,
            data=form_data,
            verify=False,
            timeout=15,
            allow_redirects=True
        )
        
        # Проверяем успешность входа
        if response.status_code != 200 or "login" in response.url.lower():
            error_msg = self.extract_error_message(response)
            if error_msg:
                raise Exception(error_msg)
            raise Exception("Authentication failed: Invalid credentials")
            
        return True
        
    # Дополнительный метод для извлечения сообщения об ошибке
    def extract_error_message(self, response):
        """Извлекает сообщение об ошибке из HTML ответа"""
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Пробуем разные стратегии поиска сообщения об ошибке
            error_selectors = [
                ('div', {'class': ['error', 'alert-error', 'alert-danger']}),
                ('span', {'class': ['error', 'kc-feedback-text']}),
                ('p', {'class': 'error'}),
                ('div', {'role': 'alert'}),
                ('div', {'id': 'input-error'})
            ]
            
            for tag, attrs in error_selectors:
                error_element = soup.find(tag, attrs)
                if error_element:
                    return error_element.get_text(strip=True)
                    
            # Если не нашли по классам, ищем по тексту
            if "invalid" in response.text.lower():
                return "Invalid credentials"
            if "username" in response.text.lower() and "password" in response.text.lower():
                return "Invalid username or password"
                
            return None
        except:
            return None
        

    def handle_direct_login(self, form, form_url, username, password):
        """Обработка прямой формы входа (без Keycloak)"""
        try:
            form_action = form.get('action')
            if not form_action:
                form_action = form_url
                
            # Собираем данные формы
            form_data = {}
            for input_tag in form.find_all(['input', 'textarea']):
                input_type = input_tag.get('type', '')
                input_name = input_tag.get('name')
                input_value = input_tag.get('value', '')
                
                # Пропускаем кнопки
                if input_type in ['submit', 'button']:
                    continue
                    
                # Обрабатываем поля
                if input_name:
                    # Для пароля используем введенный пароль
                    if input_type == 'password':
                        form_data[input_name] = password
                    # Для чекбоксов и радиокнопок
                    elif input_type in ['checkbox', 'radio']:
                        if input_tag.get('checked'):
                            form_data[input_name] = input_value
                    # Для текстовых полей
                    else:
                        # Для username используем введенное имя
                        if input_name.lower() in ['username', 'email', 'login']:
                            form_data[input_name] = username
                        else:
                            form_data[input_name] = input_value
            
            # Отправляем форму
            response = self.session.post(
                form_action,
                data=form_data,
                verify=False,
                timeout=15,
                allow_redirects=True
            )
            
            # Проверяем успешность входа
            if response.status_code != 200 or "login" in response.url.lower():
                error_msg = self.extract_error_message(response)
                if error_msg:
                    raise Exception(error_msg)
                raise Exception("Direct authentication failed: Unknown error")
                
            return True
            
        except Exception as e:
            raise Exception(f"Direct login failed: {str(e)}")

    def test_kafka_ui_connection(self):
        """Проверка подключения к Kafka UI"""
        url = self.kafka_ui_url_entry.get().strip()
        user = self.kafka_ui_user_entry.get().strip()
        password = self.kafka_ui_pass_entry.get().strip()
        
        if not url:
            messagebox.showwarning("Warning", "Please enter Kafka UI URL")
            return
            
        try:
            # Выполняем вход через Keycloak
            self.kafka_ui_login(url, user, password)
            
            # Проверяем доступ к API
            test_url = f"{url.rstrip('/')}/api/clusters"
            response = self.session.get(test_url, verify=False, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Проверяем разные форматы ответа
                    if isinstance(data, list):
                        clusters = data
                    elif isinstance(data, dict) and 'clusters' in data:
                        clusters = data['clusters']
                    elif isinstance(data, dict) and 'content' in data:
                        clusters = data['content']
                    else:
                        clusters = []
                    
                    if clusters:
                        # Берем первый кластер
                        self.cluster_name = clusters[0]['name']
                        messagebox.showinfo("Success", f"Connected to cluster: {self.cluster_name}")
                    else:
                        messagebox.showinfo("Success", "Connection successful but no clusters found")
                except json.JSONDecodeError:
                    messagebox.showerror("Error", "Invalid JSON response from Kafka UI")
            else:
                messagebox.showerror("Error", 
                    f"Connection failed: HTTP {response.status_code}\n{response.text[:200]}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")


    def show_topic_context_menu(self, event):
        """Показывает контекстное меню для топика"""
        item = self.ui_data_tree.identify_row(event.y)
        if not item:
            return
            
        self.ui_data_tree.selection_set(item)
        topic_name = self.ui_data_tree.item(item, "values")[0]
        
        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label="Open", command=lambda: self.open_topic_messages(topic_name))
        menu.tk_popup(event.x_root, event.y_root)

    def show_message_context_menu(self, event):
        """Показывает контекстное меню для сообщения"""
        item = self.dlq_tree.identify_row(event.y)
        if not item:
            return
            
        self.dlq_tree.selection_set(item)
        values = self.dlq_tree.item(item, "values")
        
        # Сохраняем выбранное сообщение для копирования
        self.selected_message = {
            'partition': values[0],
            'offset': values[1],
            'key': values[2],
            'value': values[3],
            'timestamp': values[4]
        }
        
        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label="Copy to Send", command=self.copy_message_to_send)
        menu.tk_popup(event.x_root, event.y_root)

    def open_topic_messages(self, topic_name):
        """Открывает окно с сообщениями топика"""
        window = tk.Toplevel(self.parent)
        window.title(f"Messages in {topic_name}")
        window.geometry("800x600")
        
        # Фрейм для управления
        control_frame = ttk.Frame(window)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(control_frame, text="Max messages:").pack(side=tk.LEFT)
        max_messages = tk.IntVar(value=100)
        ttk.Entry(control_frame, textvariable=max_messages, width=10).pack(side=tk.LEFT, padx=5)
        
        load_btn = ttk.Button(control_frame, text="Load Messages", 
                            command=lambda: self.load_topic_messages(topic_name, max_messages.get(), tree))
        load_btn.pack(side=tk.LEFT)
        
        # Treeview для сообщений
        columns = ('partition', 'offset', 'key', 'value', 'timestamp')
        tree = ttk.Treeview(window, columns=columns, show='headings')
        
        tree.heading('partition', text='Partition')
        tree.heading('offset', text='Offset')
        tree.heading('key', text='Key')
        tree.heading('value', text='Value')
        tree.heading('timestamp', text='Timestamp')
        
        for col in columns:
            tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(window, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Привязка контекстного меню к сообщениям
        tree.bind("<Button-3>", lambda e: self.show_message_in_context_menu(e, tree))

    def show_message_in_context_menu(self, event, tree):
        """Показывает контекстное меню для сообщения в окне топика"""
        item = tree.identify_row(event.y)
        if not item:
            return
            
        tree.selection_set(item)
        values = tree.item(item, "values")
        
        # Сохраняем выбранное сообщение
        self.selected_message = {
            'partition': values[0],
            'offset': values[1],
            'key': values[2],
            'value': values[3],
            'timestamp': values[4]
        }
        
        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label="Copy to Send", command=self.copy_message_to_send)
        menu.tk_popup(event.x_root, event.y_root)

    def load_topic_messages(self, topic, max_messages, tree):
        """Загружает сообщения из топика в окно просмотра"""
        tree.delete(*tree.get_children())
        tree.insert('', 'end', values=("Loading...", "", "", "", ""))
        
        threading.Thread(
            target=self._load_topic_messages_async,
            args=(topic, max_messages, tree),
            daemon=True
        ).start()

    def _on_assign_callback(self, consumer, partitions):
        """Callback при назначении партиций"""
        # Проверяем, есть ли назначенные партиции
        if not partitions:
            consumer.unsubscribe()
            raise Exception("No partitions assigned. Check topic exists and consumer group")
        
        # Сбрасываем смещение на начало
        for p in partitions:
            p.offset = OFFSET_BEGINNING
        consumer.assign(partitions)

    def _load_topic_messages_async(self, topic, max_messages, tree):
        """Асинхронная загрузка сообщений топика"""
        try:
            conf = self.get_consumer_config(topic)
            consumer = Consumer(conf)
            consumer.subscribe([topic], on_assign=self._on_assign_callback)
            
            messages = []
            msg_count = 0
            start_time = datetime.now()
            
            while msg_count < max_messages:
                msg = consumer.poll(1.0)
                if msg is None:
                    if (datetime.now() - start_time).seconds > 10:
                        break
                    continue
                    
                if msg.error():
                    continue
                    
                # Форматируем время
                ts_type, ts_val = msg.timestamp()
                if ts_type == 0:  # CREATE_TIME
                    ts_str = datetime.fromtimestamp(ts_val/1000).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    ts_str = "N/A"
                
                try:
                    key = msg.key().decode('utf-8') if msg.key() else ''
                except UnicodeDecodeError:
                    key = str(msg.key())[:50] + '...' if msg.key() else ''
                
                try:
                    value = msg.value().decode('utf-8') if msg.value() else ''
                except UnicodeDecodeError:
                    value = str(msg.value())[:100] + '...' if msg.value() else ''
                
                messages.append({
                    'partition': msg.partition(),
                    'offset': msg.offset(),
                    'key': key,
                    'value': value,
                    'timestamp': ts_str
                })
                
                msg_count += 1
                    
            consumer.close()
            
            # Обновляем UI в основном потоке
            self.parent.after(0, lambda: self.update_topic_tree(tree, messages))
            
        except Exception as e:
            self.parent.after(0, lambda e=e: messagebox.showerror(
                "Error", 
                f"Failed to load messages: {str(e)}\n"
                "Check bootstrap servers and security settings"
            ))

    def update_topic_tree(self, tree, messages):
        """Обновляет Treeview с сообщениями топика"""
        tree.delete(*tree.get_children())
        
        if not messages:
            tree.insert('', 'end', values=("No messages found", "", "", "", ""))
            return
            
        for msg in messages:
            value_preview = msg['value'][:100] + '...' if len(msg['value']) > 100 else msg['value']
            tree.insert('', 'end', values=(
                msg['partition'],
                msg['offset'],
                msg['key'],
                value_preview,
                msg['timestamp']
            ))

    def copy_message_to_send(self):
        """Копирует выбранное сообщение в основное окно"""
        if not hasattr(self, 'selected_message') or not self.selected_message:
            return
            
        full_message = self.selected_message['value']
        
        # Пытаемся получить полное сообщение
        if '...' in full_message and hasattr(self, 'dlq_messages'):
            # Ищем полное сообщение в кеше
            for msg in self.dlq_messages:
                if (str(msg['partition']) == self.selected_message['partition'] and
                    str(msg['offset']) == self.selected_message['offset']):
                    full_message = msg['value']
                    break
        
        # Вставляем в редактор сообщений
        self.message_editor.delete('1.0', tk.END)
        self.message_editor.insert('1.0', full_message)
        
        # Автоматическая валидация JSON
        self.json_check.set(True)
        if self.json_check.get():
            try:
                json.loads(full_message)
                messagebox.showinfo("Valid JSON", "Message is valid JSON")
            except json.JSONDecodeError as e:
                messagebox.showerror("Invalid JSON", f"JSON Error: {str(e)}")
        
        # Переключаемся на вкладку Main
        self.notebook.select(0)
    
    def load_kafka_ui_data(self):
        """Загрузка данных из Kafka UI с оптимизациями"""
        url = self.kafka_ui_url_entry.get().strip()
        user = self.kafka_ui_user_entry.get().strip()
        password = self.kafka_ui_pass_entry.get().strip()
        data_type = self.data_type_combobox.get().lower()
        
        if not url:
            messagebox.showwarning("Warning", "Please enter Kafka UI URL")
            return
            
        # Проверка кэша
        if self._check_cache(data_type):
            self.parent.after(0, self.update_ui_data_tree, data_type, self.cache[data_type]['data'])
            return
            
        # Показать индикатор загрузки
        self.load_data_btn.config(state=tk.DISABLED)
        self.ui_data_tree.delete(*self.ui_data_tree.get_children())
        self.ui_data_tree.insert('', 'end', values=("Loading...", "", ""))
        self.loading_canceled = False
        
        # Запуск в фоновом потоке
        threading.Thread(
            target=self._load_kafka_ui_data_async,
            args=(url, user, password, data_type),
            daemon=True
        ).start()


    def _load_kafka_ui_data_async(self, url, user, password, data_type):
        """Асинхронная загрузка данных с пагинацией и параллелизмом"""
        try:
            # Выполняем вход (если необходимо)
            if not self.session.cookies:
                self.kafka_ui_login(url, user, password)
            
            # Формируем базовый URL
            api_url = f"{url.rstrip('/')}/api/clusters/{self.cluster_name}"
            if data_type == 'topics':
                api_url += "/topics"
            elif data_type == 'brokers':
                api_url += "/brokers"
            elif data_type == 'consumers':
                api_url += "/consumers"
            
            # Параллельная загрузка страниц
            max_pages = 5  # Ограничение количества страниц
            per_page = 100  # Записей на страницу
            all_data = []
            
            if data_type == 'topics':
                # Для топиков используем последовательную загрузку
                page = 1
                while page <= max_pages and not self.loading_canceled:
                    page_data = self._load_page(api_url, page, per_page)
                    if not page_data:
                        break
                    all_data.extend(page_data)
                    page += 1
            else:
                # Для брокеров и консюмеров - параллельная загрузка
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(self._load_page, api_url, p, per_page) 
                              for p in range(1, max_pages+1)]
                    
                    for future in as_completed(futures):
                        if self.loading_canceled:
                            break
                        page_data = future.result()
                        if page_data:
                            all_data.extend(page_data)
            
            if self.loading_canceled:
                return
                
            # Сохраняем в кэш
            self.cache[data_type] = {
                'data': all_data,
                'timestamp': time.time()
            }
            
            # Обновляем UI
            self.parent.after(0, self.update_ui_data_tree, data_type, all_data)
            
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to load data: {str(e)}"))
        finally:
            self.parent.after(0, lambda: self.load_data_btn.config(state=tk.NORMAL))


    def _load_page(self, api_url, page, per_page):
        """Загрузка одной страницы данных"""
        try:
            paginated_url = f"{api_url}?page={page}&perPage={per_page}"
            response = self.session.get(paginated_url, verify=False, timeout=15)
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            
            # Извлекаем элементы из ответа
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if 'content' in data:
                    items = data['content']
                elif 'topicList' in data:
                    items = data['topicList']
                elif 'topics' in data:
                    items = data['topics']
                elif 'brokers' in data:
                    items = data['brokers']
                elif 'consumers' in data:
                    items = data['consumers']
                else:
                    # Поиск первого списка в словаре
                    for key in data:
                        if isinstance(data[key], list):
                            items = data[key]
                            break
            return items
        except Exception as e:
            print(f"Error loading page: {str(e)}")
            return []  # Возвращаем пустой список вместо None
    
    def _check_cache(self, data_type):
        """Проверяет актуальность кэша"""
        cache_entry = self.cache.get(data_type)
        if cache_entry and cache_entry['data']:
            return time.time() - cache_entry['timestamp'] < self.cache_timeout
        return False
    
    def update_ui_data_tree(self, data_type, all_data):
        """Обновление Treeview с оптимизацией производительности"""
        self.ui_data_tree.delete(*self.ui_data_tree.get_children())
        
        if not all_data:
            self.ui_data_tree.insert('', 'end', values=("No data found", "", ""))
            return
            
        # Для больших наборов данных - ограничение отображения
        display_data = all_data[:500]  # Показываем только первые 500 элементов
        
        # Пакетное добавление элементов
        items_to_insert = []
        
        if data_type == 'topics':
            # Фильтрация DLQ топиков
            if data_type == 'topics' and self.filter_dlq.get():
                display_data = [
                    topic for topic in display_data 
                    if isinstance(topic, dict) and 'dlq' in topic.get('name', '').lower()
                ]
            
            for topic in display_data:
                if not isinstance(topic, dict):
                    continue
                partitions = len(topic.get('partitions', []))
                items_to_insert.append((
                    topic.get('name', ''),
                    'Topic',
                    f"Partitions: {partitions} | Size: {topic.get('size', 0)}"
                ))
                
            # Обновление списка DLQ топиков
            dlq_topic_names = [
                topic.get('name', '') 
                for topic in all_data 
                if isinstance(topic, dict) and 'dlq' in topic.get('name', '').lower()
            ]
            self.dlq_topic_combobox['values'] = dlq_topic_names
            
        elif data_type == 'brokers':
            for broker in display_data:
                if not isinstance(broker, dict):
                    continue
                items_to_insert.append((
                    broker.get('host', ''),
                    'Broker',
                    f"ID: {broker.get('id', '')} | Port: {broker.get('port', 0)}"
                ))
                
        elif data_type == 'consumers':
            for consumer in display_data:
                if not isinstance(consumer, dict):
                    continue
                items_to_insert.append((
                    consumer.get('groupId', ''),
                    'Consumer Group',
                    f"Members: {consumer.get('members', 0)} | Lag: {consumer.get('lag', 0)}"
                ))
        
        # Массовая вставка элементов
        for item in items_to_insert:
            self.ui_data_tree.insert('', 'end', values=item)
        #self.ui_data_tree.config(state=tk.NORMAL)
        
        # Статусная информация
        status = f"Showing {len(display_data)} of {len(all_data)} items"
        if data_type == 'topics' and self.filter_dlq.get():
            status = f"Showing {len(display_data)} DLQ topics"
        self.parent.after(0, lambda: messagebox.showinfo("Info", status))
    
    def cancel_loading(self):
        """Отмена текущей операции загрузки"""
        self.loading_canceled = True
        self.load_data_btn.config(state=tk.NORMAL)
        self.ui_data_tree.delete(*self.ui_data_tree.get_children())
        self.ui_data_tree.insert('', 'end', values=("Loading canceled", "", ""))

    def start_dlq_loading(self):
        """Запускает поток для загрузки DLQ сообщений"""
        dlq_topic = self.dlq_topic_combobox.get()
        if not dlq_topic:
            messagebox.showwarning("Warning", "Select DLQ topic")
            return
            
        self.dlq_tree.delete(*self.dlq_tree.get_children())
        self.load_dlq_btn.config(state=tk.DISABLED)
        self.refresh_dlq_btn.config(state=tk.DISABLED)
        self.dlq_tree.insert('', 'end', values=("Loading...", "", "", "", ""))
        
        # Запуск в отдельном потоке
        threading.Thread(
            target=self.load_dlq_messages, 
            args=(dlq_topic,),
            daemon=True
        ).start()
        
    def load_dlq_topics(self):
        """Загружает список топиков для DLQ"""
        try:
            conf = {'bootstrap.servers': self.bootstrap_entry.get()}
            admin = AdminClient(conf)
            topics = admin.list_topics().topics
            # Фильтруем только DLQ-топики
            dlq_topics = [topic for topic in topics if 'dlq' in topic.lower()]
            self.dlq_topic_combobox['values'] = dlq_topics
            
            if dlq_topics:
                messagebox.showinfo("Info", f"Found {len(dlq_topics)} DLQ topics")
            else:
                messagebox.showinfo("Info", "No DLQ topics found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load topics: {str(e)}")
        
    def load_dlq_messages(self, topic):
        """Загружает сообщения из DLQ топика"""
        try:
            conf = self.get_consumer_config(topic)
            consumer = Consumer(conf)
            consumer.subscribe([topic])
            
            # Очищаем предыдущие сообщения
            self.dlq_messages = []
            
            # Получаем сообщения
            msg_count = 0
            start_time = datetime.now()
            
            while msg_count < 100:  # Ограничиваем количество сообщений
                msg = consumer.poll(1.0)
                if msg is None:
                    # Проверяем, не прошло ли уже 10 секунд
                    if (datetime.now() - start_time).seconds > 10:
                        break
                    continue
                    
                if msg.error():
                    continue
                    
                # Форматируем время
                ts_type, ts_val = msg.timestamp()
                if ts_type == 0:  # CREATE_TIME
                    ts_str = datetime.fromtimestamp(ts_val/1000).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    ts_str = "N/A"
                
                try:
                    key = msg.key().decode('utf-8') if msg.key() else ''
                except UnicodeDecodeError:
                    key = str(msg.key())[:50] + '...' if msg.key() else ''
                
                try:
                    value = msg.value().decode('utf-8') if msg.value() else ''
                except UnicodeDecodeError:
                    value = str(msg.value())[:100] + '...' if msg.value() else ''
                
                # Сохраняем полное сообщение
                full_value = msg.value().decode('utf-8') if msg.value() else ''
                
                self.dlq_messages.append({
                    'partition': msg.partition(),
                    'offset': msg.offset(),
                    'key': key,
                    'value': full_value,  # Сохраняем полное сообщение
                    'timestamp': ts_str
                })
                
                msg_count += 1
                    
            consumer.close()
            
            # Обновляем UI в основном потоке
            self.parent.after(0, self.update_dlq_tree)
            
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Error", f"Failed to load DLQ messages: {str(e)}"))
        finally:
            self.parent.after(0, lambda: self.load_dlq_btn.config(state=tk.NORMAL))
            self.parent.after(0, lambda: self.refresh_dlq_btn.config(state=tk.NORMAL))
            
    def update_dlq_tree(self):
        """Обновляет Treeview с DLQ сообщениями"""
        self.dlq_tree.delete(*self.dlq_tree.get_children())
        
        if not self.dlq_messages:
            self.dlq_tree.insert('', 'end', values=("No messages found", "", "", "", ""))
            return
            
        for msg in self.dlq_messages:
            value_preview = msg['value'][:100] + '...' if len(msg['value']) > 100 else msg['value']
            self.dlq_tree.insert('', 'end', values=(
                msg['partition'],
                msg['offset'],
                msg['key'],
                value_preview,
                msg['timestamp']
            ))
        
    def get_consumer_config(self, topic):
        """Возвращает конфигурацию для потребителя DLQ"""
        conf = {
        'bootstrap.servers': self.bootstrap_entry.get(),
        'group.id': f'dlq-viewer-{topic}-{datetime.now().timestamp()}',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
        'session.timeout.ms': 10000,
        # Добавляем настройку для принудительного использования IPv4
        'client.dns.lookup': 'use_all_dns_ips',
        # Явно указываем использовать IPv4
        #'socket.family.id': socket.AF_INET
        }
        
        protocol = self.security_protocol.get()
        if protocol:
            conf['security.protocol'] = protocol
            
        # SSL settings
        if self.ssl_ca_entry.get():
            conf['ssl.ca.location'] = self.ssl_ca_entry.get()
            
        # SASL settings
        if self.sasl_user_entry.get():
            conf.update({
                'sasl.mechanism': 'PLAIN',  #self.default_config['sasl_mechanism'],
                'sasl.username': self.sasl_user_entry.get(),
                'sasl.password': self.sasl_pass_entry.get()
            })
            
        return conf

    def update_security_fields(self, event=None):
        protocol = self.security_protocol.get()
        ssl_enabled = 'SSL' in protocol
        sasl_enabled = 'SASL' in protocol
        
        self.ssl_ca_entry.config(state='normal' if ssl_enabled else 'disabled')
        self.sasl_user_entry.config(state='normal' if sasl_enabled else 'disabled')
        self.sasl_pass_entry.config(state='normal' if sasl_enabled else 'disabled')

    def parse_headers(self):
        headers = []
        raw_headers = self.headers_entry.get().split(',')
        for header in raw_headers:
            if ':' in header:
                key, value = header.split(':', 1)
                headers.append((key.strip(), value.strip().encode('utf-8')))
        return headers
        
    def load_topics(self):
        try:
            # Используем общий метод для получения конфигурации
            conf = self.get_producer_config()
            # Для AdminClient нужно удалить client.id (не поддерживается)
            conf.pop('client.id', None)
            
            admin = AdminClient(conf)
            topics = admin.list_topics(timeout=10).topics  # Таймаут 10 секунд
            self.topic_combobox['values'] = list(topics.keys())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load topics: {str(e)}")
            
    def get_producer_config(self):
        conf = {
            'bootstrap.servers': self.bootstrap_entry.get(),
            'client.id': socket.gethostname(),
            'client.dns.lookup': 'use_all_dns_ips',
            #'socket.family.id': socket.AF_INET  # автоматическое преобразование в AF_INET
        }
        
        protocol = self.security_protocol.get()
        if protocol:
            conf['security.protocol'] = protocol
            
        if self.ssl_ca_entry.get():
            conf['ssl.ca.location'] = self.ssl_ca_entry.get()
                
        if self.sasl_user_entry.get():
            conf.update({
                'sasl.mechanism': self.default_config['sasl_mechanism'],
                'sasl.username': self.sasl_user_entry.get(),
                'sasl.password': self.sasl_pass_entry.get()
            })
                
        return conf
    
    def test_kafka_connection(self):
        """Проверка подключения к Kafka"""
        try:
            conf = self.get_producer_config()
            # Удаляем client.id для AdminClient
            conf.pop('client.id', None)
            
            admin = AdminClient(conf)
            # Получаем метаданные с таймаутом
            metadata = admin.list_topics(timeout=10)
            
            if metadata.brokers:
                broker_info = "\n".join(
                    [f"Broker {b.broker_id}: {b.host}:{b.port}" 
                    for b in metadata.brokers.values()]
                )
                messagebox.showinfo(
                    "Connection Successful", 
                    f"Connected to Kafka cluster\n\n{broker_info}"
                )
            else:
                messagebox.showerror("Error", "No brokers found")
                
        except Exception as e:
            messagebox.showerror(
                "Connection Failed", 
                f"Failed to connect to Kafka: {str(e)}\n"
                "Check bootstrap servers and security settings"
            )

    
    def validate_json(self, data):
        try:
            json.loads(data)
            return True
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Error", f"Invalid JSON: {str(e)}")
            return False
            
    def format_json(self):
        try:
            data = json.loads(self.message_editor.get('1.0', tk.END))
            formatted = json.dumps(data, indent=2)
            self.message_editor.delete('1.0', tk.END)
            self.message_editor.insert('1.0', formatted)
        except Exception as e:
            messagebox.showerror("Format Error", str(e))
    
    def add_to_history(self, topic, key, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.history.append({
            'time': timestamp,
            'topic': topic,
            'key': key,
            'message': message[:50] + '...' if len(message) > 50 else message
        })
        
        if len(self.history) > self.history_limit:
            self.history.pop(0)
            
        self.update_history_tree()
    
    def update_history_tree(self):
        self.history_tree.delete(*self.history_tree.get_children())
        for item in self.history:
            self.history_tree.insert('', 'end', values=(
                item['time'],
                item['topic'],
                item['key'],
                item['message']
            ))
    
    def clear_history(self):
        self.history.clear()
        self.update_history_tree()
        
    def send_message(self):
        # Validate security settings
        protocol = self.security_protocol.get()
        if protocol in ['SASL_PLAIN', 'SASL_SSL'] and not all([
            self.sasl_user_entry.get(),
            self.sasl_pass_entry.get()
        ]):
            messagebox.showerror("Error", "SASL requires username and password")
            return
            
        if protocol in ['SSL', 'SASL_SSL'] and not self.ssl_ca_entry.get():
            messagebox.showerror("Error", "SSL requires CA certificate path")
            return

        config = self.get_producer_config()
        topic = self.topic_combobox.get()
        key = self.key_entry.get()
        message = self.message_editor.get('1.0', tk.END).strip()
        
        if not topic:
            messagebox.showerror("Error", "Please select or enter a topic")
            return
            
        if not message:
            messagebox.showerror("Error", "Message cannot be empty")
            return
            
        if self.json_check.get() and not self.validate_json(message):
            return
            
        try:
            producer = Producer(config)

            # Парсим заголовки
            headers = self.parse_headers()
            
            # Парсим партицию
            partition = None
            if self.partition_entry.get():
                try:
                    partition = int(self.partition_entry.get())
                except ValueError:
                    messagebox.showerror("Error", "Partition must be integer")
                    return
            
            def delivery_report(err, msg):
                if err:
                    messagebox.showerror("Delivery Failed", str(err))
                else:
                    self.add_to_history(topic, key, message)
                    messagebox.showinfo("Success", 
                        f"Delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")
            
            producer.produce(
                topic=topic,
                key=key,
                value=message,
                headers=headers,
                partition=partition,
                callback=delivery_report
            )
            
            producer.flush()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send message: {str(e)}")

    # Добавляем функцию для создания экземпляра приложения в Toplevel
def create_kafka_tool(parent=None):
    if parent is None:
        parent = tk.Tk()
    return KafkaProducerApp(parent)

if __name__ == "__main__":
    parent = tk.Tk()
    app = KafkaProducerApp(parent)
    parent.mainloop()