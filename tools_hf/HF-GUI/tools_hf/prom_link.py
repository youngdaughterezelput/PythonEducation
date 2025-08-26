import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
from urllib.parse import unquote, urlparse, parse_qs, quote
import re
from datetime import datetime, timedelta
import logging
import json
import html
import csv
import os
import pandas as pd
import os
from tkcalendar import DateEntry
import webbrowser

# Предопределенные функции для конкретных алертов
PREDEFINED_EXPRESSIONS = {
    "resultCode-omni-prod": "max by (result_code, result_message, status, uri, service, namespace) (increase(http_server_requests_seconds_count{namespace=~\"^omni-.*-prod$\",result_code=~\"^01.*|^02.*\",uri!~\"/health|/metrics\"}[5m])) > 0",
    "resultCode-self-bff-omni-prod": "max by (result_code, result_message, status, uri, service, namespace) (increase(bff_self_api_response_codes_total{namespace=~\"^omni-.*-prod$\",result_code!~\"01509\",result_code=~\"^01.*|^02.*\",uri!~\"/health|/metrics\"}[5m])) > 0",
    "request-latency-sum-omni-prod": "rate(http_server_requests_seconds_sum{namespace=~\"^omni-.*-prod$\",uri!~\"/health|/metrics\"}[5m]) / rate(http_server_requests_seconds_count{namespace=~\"^omni-.*-prod$\",uri!~\"/health|/metrics\"}[5m]) > 1",
    "service-bff-error-4xx-5xx-omni-prod": "sum by (status, service, method, route, namespace) (increase(ktor_http_server_requests_seconds_count{route!~\"/metrics|/health\",status!~\"422\",status=~\"5..|4..\"}[3m])) > 0",
    "request-latency-max-omni-prod": "sum by (method, status, uri, namespace) (http_server_requests_seconds_max{namespace=~\"^omni-.*-prod$\",uri!~\"/health|/metrics\"} > 5)",
    "service-error-4xx-5xx-omni-prod": "sum by (status, service, method, uri, namespace) (increase(http_server_requests_seconds_count{status=~\"5..|4..\",uri!~\"/metrics|/health\"}[3m])) > 0",
    "resultCode-external-bff-omni-prod": "max by (result_code, result_message, status, uri, service, namespace) (increase(bff_external_api_response_codes_total{namespace=~\"^omni-.*-prod$\",result_code=~\"^01.*|^02.*\",uri!~\"/health|/metrics\"}[5m])) > 0",
    #выражения для prom-ld-001
    "TooManyRejectedPayments24h": "delta(omni_billing_payment{payment_status=\"REJECTED\"}[24h]) > 5",
    "CheckoutOrderNotSentToKafka": "omni_checkout_not_sent_to_kafka > 0",
    "CPUIdle": "(avg by (dip1_server) (rate(node_cpu_seconds_total{dip1_server=~\"pgdb-1d-omni-0.*|pgdb-1s.*\",mode=\"idle\"}[3m])) * 100) < 5",
    "CPUIdle_001_002": "((avg by (dbpl_server) (rate(node_cpu_seconds_total{dbpl_server=~\"pgdb-1d-omni-001|pgdb-1d-omni-002\",mode=\"idle\"}[5m])) * 100) < 5",
    "DiskSpaceFree-pgdb-Id-omni": "(node_filesystem_avail_bytes{dbpl_server=~\"pgdb-1d-omni-0.*|pgdb-1s.*\",job=\"dbpl-node\"} * 100) / node_filesystem_size_bytes{dbpl_server=~\"pgdb-1d-omni-0.*|pgdb-1s.*\", job=\"dbpl-node\"} < 10 and node_filesystem_readonly{dbpl_server=~\"pgdb-1d-omni-0.*|pgdb-1s.*\", job=\"dbpl-node\"} == 0",
    "HostOomKillDetected-pgdb-ld-omni": "increase(node_vmstat_oom_kill{dbpl_server=~\"pgdb-ld-omni-0.*|pgdb-1s.*\"}[1m]) > 0",
    "AverageDiskQueueOver150For10m-pgdb-ld-omni": "rate(node_disk_io_time_weighted_seconds_total{dbpl_server=~\"pgdb-ld-omni-0.*|pgdb-1s.*\"}[5m]) > 150",
    "AvgMessageSizeByTopic-omni-prod": "(sum by (topic) (kafka_log_log_size{job=~\"kafka_omni_prod\",topic!~\".*dlq.*\",topic!~\"^__.+|.+?schema.+|dbz_[0-9]_connect.+\"}) / (sum by (topic) (kafka_topic_partition_current_offset{job=~\"kafka_omni_prod\",topic!~\".*dlq.*\",topic!~\"^__.+|.+?schema.+|dbz_[0-9]_connect.+\"} - kafka_topic_partition_oldest_offset{job=~\"kafka_omni_prod\",topic!~\".*dlq.*\",topic!~\"^__.+|.+?schema.+|dbz_[0-9]_connect.+\"}))) > 10240",
}

import os
import re
from dotenv import load_dotenv

class ServerManager:
    """Класс для управления серверами Prometheus"""
    DEFAULT_SERVERS = {
        "Server OMNI metrics": "http://omni.prometheus-prod.kifr-ru.local/",
        "Rules metrics": "http://prom-ld-001:9090/"
    }
    
    def __init__(self):
        self.servers = self.load_servers()
        
    def load_servers(self):
        """Загрузка серверов из .env файла"""
        load_dotenv()
        servers = self.DEFAULT_SERVERS.copy()
        
        # Загрузка пользовательских серверов
        custom_servers = os.getenv("CUSTOM_SERVERS", "")
        if custom_servers:
            try:
                custom_servers = json.loads(custom_servers)
                servers.update(custom_servers)
            except json.JSONDecodeError:
                pass
                
        return servers
    
    def save_servers(self):
        """Сохранение пользовательских серверов в .env"""
        # Пока сохраняем только пользовательские серверы, отличные от дефолтных
        custom_servers = {k: v for k, v in self.servers.items() 
                          if k not in self.DEFAULT_SERVERS}
        
        # Читаем существующее содержимое .env
        env_lines = []
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                env_lines = f.readlines()
                
        # Удаляем старые настройки серверов
        new_lines = []
        for line in env_lines:
            if not line.startswith("CUSTOM_SERVERS="):
                new_lines.append(line)
                
        # Добавляем новые настройки
        new_lines.append(f'CUSTOM_SERVERS={json.dumps(custom_servers)}\n')
        
        # Сохраняем файл
        with open(".env", "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
    def get_server_names(self):
        """Получение списка имен серверов"""
        return list(self.servers.keys()) + ["Все серверы"]
    
    def get_server_url(self, name):
        """Получение URL по имени сервера"""
        if name == "Все серверы":
            return None
        return self.servers.get(name)
    
    def add_custom_server(self, name, url):
        """Добавление пользовательского сервера"""
        self.servers[name] = url
        self.save_servers()

class AlertConfigManager:
    """Класс для управления конфигурацией алертов с использованием .env файла"""
    ENV_FILE = ".env"
    
    def __init__(self):
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Загрузка конфигурации из .env файла"""
        # Создаем файл, если его нет
        if not os.path.exists(self.ENV_FILE):
            open(self.ENV_FILE, 'w').close()
        
        # Загружаем переменные окружения
        load_dotenv(self.ENV_FILE)
        
        # Собираем все переменные, начинающиеся с ALERT_
        self.config = {}
        for key, value in os.environ.items():
            if key.startswith("ALERT_"):
                alert_name = key[6:]  # Убираем префикс ALERT_
                self.config[alert_name] = value
    
    def save_config(self):
        """Сохранение конфигурации в .env файл"""
        # Читаем существующее содержимое файла
        existing_lines = []
        if os.path.exists(self.ENV_FILE):
            with open(self.ENV_FILE, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # Удаляем все существующие записи об алертах
        new_lines = []
        for line in existing_lines:
            if not re.match(r'^\s*ALERT_', line) and not re.match(r'^\s*#', line):
                new_lines.append(line)
        
        # Добавляем новые записи об алертах
        for alert_name, expression in self.config.items():
            # Экранируем специальные символы
            escaped_expr = expression.replace('"', '\\"')
            new_lines.append(f'ALERT_{alert_name}="{escaped_expr}"\n')
        
        # Сохраняем обновленный файл
        with open(self.ENV_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        # Обновляем переменные окружения
        load_dotenv(self.ENV_FILE, override=True)
    
    def get_expression(self, alert_name):
        """Получение выражения для алерта"""
        # Сначала проверяем пользовательскую конфигурацию
        if alert_name in self.config:
            return self.config[alert_name]
        
        # Затем проверяем предопределенные выражения
        if alert_name in PREDEFINED_EXPRESSIONS:
            return PREDEFINED_EXPRESSIONS[alert_name]
        
        return None
    
    def set_expression(self, alert_name, expression):
        """Установка выражения для алерта"""
        self.config[alert_name] = expression
        self.save_config()

class DataFetcher:
    """Класс для получения данных из Prometheus"""
    def __init__(self, server_manager, selected_server):
        self.server_manager = server_manager
        self.selected_server = selected_server
        self.logger = logging.getLogger(__name__)
        self.config_manager = AlertConfigManager()
        
    def get_prometheus_url(self):
        """Получение URL выбранного сервера"""
        if self.selected_server == "Все серверы":
            return None
        return self.server_manager.get_server_url(self.selected_server)
        
    def fetch_alert_expression(self, alert_name):
        """Получение выражения метрики из страницы правил Prometheus"""
        try:
            prom_url = self.get_prometheus_url()
            if not prom_url:
                return None
                
            response = requests.get(f"{prom_url}/rules", timeout=10)
            response.raise_for_status()
            
            pattern = re.compile(
                rf'<a href="/rules\?rule_group=.+?">{re.escape(alert_name)}</a>.*?<pre>(.*?)</pre>',
                re.DOTALL
            )
            
            matches = pattern.findall(response.text)
            if matches:
                expr = matches[0].strip()
                expr = html.unescape(expr)
                expr = expr.replace('\n', ' ')
                return re.sub(r'\s+', ' ', expr)
            
            return None
        except Exception as e:
            self.logger.error(f"Ошибка получения выражения из правил: {str(e)}")
            return None

    def query_range(self, query, start, end, step):
        """Выполнение диапазонного запроса к Prometheus API"""
        try:
            prom_url = self.get_prometheus_url()
            if not prom_url:
                raise ValueError("Не выбран сервер Prometheus")
                
            url = f"{prom_url}/api/v1/query_range"
            params = {
                'query': query,
                'start': start,
                'end': end,
                'step': step
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                error_msg = data.get('error', 'Unknown error')
                raise Exception(f"Prometheus API error: {error_msg}")
            
            return data['data']
        except Exception as e:
            self.logger.error(f"Ошибка запроса: {str(e)}")
            params_debug = {k: v for k, v in params.items()}
            params_debug['query'] = f"{params_debug['query'][:50]}..." if len(params_debug['query']) > 50 else params_debug['query']
            raise Exception(f"Ошибка запроса к Prometheus: {str(e)}\nПараметры: {json.dumps(params_debug, indent=2)}")

    def extract_expr_from_url(self, url):
        """Извлечение выражения метрики из URL"""
        try:
            prom_url = self.get_prometheus_url()
            if prom_url and prom_url in url:
                url = url.replace(prom_url, '', 1)
            
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            
            for key in ['g0.expr', 'expr', 'g0.expr[]', 'expr[]']:
                if key in query:
                    return unquote(query[key][0])
            
            if parsed.fragment:
                frag_params = parse_qs(parsed.fragment)
                for key in ['g0.expr', 'expr']:
                    if key in frag_params:
                        return unquote(frag_params[key][0])
            
            match = re.search(r'(?:g0\.expr|expr)=([^&]+)', url)
            if match:
                return unquote(match.group(1))
            
            return None
        except Exception as e:
            self.logger.error(f"Ошибка извлечения выражения из URL: {str(e)}")
            return None

    def get_metric_data(self, alert_data, start, end, step, custom_query=None):
        """Основной метод для получения данных метрики с поддержкой кастомных запросов"""
        # Если передан кастомный запрос, используем его
        if custom_query is not None:
            expr = custom_query
        else:
            # Иначе извлекаем выражение как обычно
            alert_name = alert_data.get('labels', {}).get('alertname')
            expr = self.config_manager.get_expression(alert_name)
            
            if not expr:
                expr = self.fetch_alert_expression(alert_name)
            
            if not expr:
                expr = self.extract_expr_from_url(alert_data.get('generatorURL', ''))
            
            if not expr:
                annotations = alert_data.get('annotations', {})
                expr = annotations.get('query', annotations.get('expr', ''))
            
            if not expr:
                labels = alert_data.get('labels', {})
                metric_name = labels.get('__name__', '')
                if metric_name:
                    base_query = f"{metric_name}"
                    for key, value in labels.items():
                        if key != '__name__':
                            base_query += f'{key}="{value}",'
                    expr = base_query.rstrip(',') + '}'
            
            if not expr:
                raise ValueError("Не удалось извлечь выражение метрики")
        
        # Выполняем запрос
        start_ts = int(start.timestamp())
        end_ts = int(end.timestamp())
        
        return self.query_range(expr, start_ts, end_ts, step), expr


class PlotBuilder:
    """Класс для построения графиков на основе данных"""
    def __init__(self, figure, alert_data):
        self.figure = figure
        self.alert_data = alert_data
        self.logger = logging.getLogger(__name__)
        self.dataframe = None
        
    def process_data(self, raw_data):
        """Обработка сырых данных и преобразование в DataFrame"""
        if raw_data.get('resultType') != 'matrix':
            raise ValueError(f"Неподдерживаемый тип данных: {raw_data.get('resultType')}. Ожидается 'matrix'.")
        
        results = raw_data.get('result', [])
        if not results:
            raise ValueError("Нет данных для отображения")
        
        # Собираем все данные в список словарей
        all_data = []
        
        for result in results:
            metric = result.get('metric', {})
            values = result.get('values', [])
            
            if not values:
                continue
                
            for value in values:
                try:
                    ts = datetime.fromtimestamp(float(value[0]))
                    val = float(value[1])
                    
                    # Создаем запись с метками и значениями
                    record = {
                        'timestamp': ts,
                        'value': val
                    }
                    
                    # Добавляем все метки
                    for k, v in metric.items():
                        record[k] = v
                    
                    all_data.append(record)
                except (ValueError, TypeError) as e:
                    self.logger.error(f"Ошибка преобразования данных: {str(e)}")
                    continue
        
        if not all_data:
            raise ValueError("Нет данных для построения после обработки")
        
        # Создаем DataFrame
        self.dataframe = pd.DataFrame(all_data)
        return self.dataframe
    
    def build_plot(self, expr):
        """Построение графика на основе обработанных данных"""
        if self.dataframe is None or self.dataframe.empty:
            raise ValueError("Нет данных для построения графика")
        
        # Очищаем график
        ax = self.figure.gca()
        ax.clear()
        
        # Группируем данные по меткам (если есть дополнительные метки)
        group_columns = [col for col in self.dataframe.columns if col not in ['timestamp', 'value']]
        grouped = self.dataframe.groupby(group_columns) if group_columns else [(None, self.dataframe)]
        
        # Ограничиваем количество рядов
        max_series = 15
        plot_data = []
        
        for group_key, group_df in grouped:
            if len(plot_data) >= max_series:
                break
                
            # Формируем метку для легенды
            if group_key is None:
                label = "value"
            else:
                if isinstance(group_key, tuple):
                    labels = [f"{k}={v}" for k, v in zip(group_columns, group_key)]
                else:
                    labels = [f"{group_columns[0]}={group_key}"]
                label = ", ".join(labels[:3]) + ("..." if len(labels) > 3 else "")
            
            # Сортируем по времени
            group_df = group_df.sort_values('timestamp')
            
            # Строим график
            ax.plot(group_df['timestamp'], group_df['value'], label=label)
            plot_data.append((label, group_df))
        
        # Добавляем пороговое значение
        alert_value = self.alert_data.get('value', '')
        try:
            threshold = float(alert_value)
            ax.axhline(y=threshold, color='r', linestyle='--', label='Порог')
        except (ValueError, TypeError):
            pass
        
        # Настройка оформления
        short_expr = expr if len(expr) <= 100 else expr[:97] + "..."
        ax.set_title(f"Метрика: {short_expr}", fontsize=12)
        ax.set_xlabel("Время", fontsize=10)
        ax.set_ylabel("Значение", fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.figure.autofmt_xdate()
        
        # Добавляем легенду если рядов не слишком много
        if len(plot_data) <= 10:
            ax.legend(loc='best', fontsize=8)
        
        return ax.figure, len(plot_data), len(grouped)
    
    def export_to_csv(self, filename):
        """Экспорт данных в CSV файл"""
        if self.dataframe is None or self.dataframe.empty:
            raise ValueError("Нет данных для экспорта")
        
        self.dataframe.to_csv(filename, index=False, encoding='utf-8')
        return filename


class AlertGraphWindow:
    """Окно для отображения графика метрики алерта"""
    def __init__(self, parent, server_manager, selected_server, alert_data):
        self.parent = parent
        self.server_manager = server_manager
        self.selected_server = selected_server
        self.alert_data = alert_data
        self.window = tk.Toplevel(parent)
        self.window.title("График метрики алерта")
        self.window.geometry("1200x900")
        
        self.data_fetcher = DataFetcher(server_manager, selected_server)
        self.plot_builder = None
        self.current_data = None
        
        self.create_widgets()
        self.fill_alert_info()
        
        # Установка начальных значений времени
        self.end_time = datetime.now()
        self.start_time = self.end_time - timedelta(hours=1)
        self.update_time_inputs()
        
        self.plot_alert_metric()
        
    def create_widgets(self):
        """Создание элементов интерфейса окна графика"""
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Фрейм для информации об алерте
        alert_info_frame = ttk.LabelFrame(main_frame, text="Детали алерта")
        alert_info_frame.pack(fill=tk.X, pady=5)
        
        columns = ("key", "value")
        self.alert_info_tree = ttk.Treeview(alert_info_frame, columns=columns, show="headings", height=3)
        self.alert_info_tree.heading("key", text="Параметр")
        self.alert_info_tree.heading("value", text="Значение")
        self.alert_info_tree.column("key", width=150)
        self.alert_info_tree.column("value", width=800)
        self.alert_info_tree.pack(fill=tk.X, padx=5, pady=5)
        
        # Фрейм для выражения алерта
        expr_frame = ttk.LabelFrame(main_frame, text="Функция алерта")
        expr_frame.pack(fill=tk.X, pady=5)
        
        self.expr_text = scrolledtext.ScrolledText(expr_frame, height=4, wrap=tk.WORD)
        self.expr_text.pack(fill=tk.X, padx=5, pady=5)
        self.expr_text.config(state=tk.DISABLED)
        
        # Фрейм для управления временным диапазоном
        time_frame = ttk.Frame(main_frame)
        time_frame.pack(fill=tk.X, pady=5)
        
        # Выбор даты и времени начала
        ttk.Label(time_frame, text="Начало:").pack(side=tk.LEFT, padx=5)
        self.start_date = DateEntry(time_frame, width=12, date_pattern='dd.mm.yyyy')
        self.start_date.pack(side=tk.LEFT, padx=5)
        
        self.start_hour = ttk.Spinbox(time_frame, from_=0, to=23, width=2)
        self.start_hour.pack(side=tk.LEFT, padx=2)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        self.start_minute = ttk.Spinbox(time_frame, from_=0, to=59, width=2)
        self.start_minute.pack(side=tk.LEFT, padx=2)
        
        # Выбор даты и времени окончания
        ttk.Label(time_frame, text="Конец:").pack(side=tk.LEFT, padx=(15, 5))
        self.end_date = DateEntry(time_frame, width=12, date_pattern='dd.mm.yyyy')
        self.end_date.pack(side=tk.LEFT, padx=5)
        
        self.end_hour = ttk.Spinbox(time_frame, from_=0, to=23, width=2)
        self.end_hour.pack(side=tk.LEFT, padx=2)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        self.end_minute = ttk.Spinbox(time_frame, from_=0, to=59, width=2)
        self.end_minute.pack(side=tk.LEFT, padx=2)
        
        # Шаг выборки
        ttk.Label(time_frame, text="Шаг:").pack(side=tk.LEFT, padx=(15, 5))
        self.step_var = tk.StringVar(value="1m")
        steps = ["15s", "30s", "1m", "5m", "15m", "30m"]
        step_combo = ttk.Combobox(time_frame, textvariable=self.step_var, values=steps, width=10)
        step_combo.pack(side=tk.LEFT, padx=5)
        
        # Кнопки управления
        button_frame = ttk.Frame(time_frame)
        button_frame.pack(side=tk.RIGHT, padx=5)
        
        refresh_btn = ttk.Button(button_frame, text="Обновить", command=self.plot_alert_metric)
        refresh_btn.pack(side=tk.LEFT, padx=2)
        
        export_btn = ttk.Button(button_frame, text="Экспорт CSV", command=self.export_to_csv)
        export_btn.pack(side=tk.LEFT, padx=2)
        
        prom_btn = ttk.Button(button_frame, text="Открыть в Prometheus", command=self.open_in_prometheus)
        prom_btn.pack(side=tk.LEFT, padx=2)
        
        edit_btn = ttk.Button(button_frame, text="Редактировать функцию", command=self.edit_expression)
        edit_btn.pack(side=tk.LEFT, padx=2)
        
        # Фрейм для графика
        graph_frame = ttk.LabelFrame(main_frame, text="График метрики")
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Создаем фигуру и холст для графика
        self.figure = Figure(figsize=(12, 6), dpi=100)
        self.plot = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Статус бар
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var.set(f"Сервер: {self.selected_server} | Инициализация...")
    
    def update_time_inputs(self):
        """Обновление полей ввода времени"""
        self.start_date.set_date(self.start_time.strftime("%d.%m.%Y"))
        self.start_hour.delete(0, tk.END)
        self.start_hour.insert(0, self.start_time.strftime("%H"))
        self.start_minute.delete(0, tk.END)
        self.start_minute.insert(0, self.start_time.strftime("%M"))
        
        self.end_date.set_date(self.end_time.strftime("%d.%m.%Y"))
        self.end_hour.delete(0, tk.END)
        self.end_hour.insert(0, self.end_time.strftime("%H"))
        self.end_minute.delete(0, tk.END)
        self.end_minute.insert(0, self.end_time.strftime("%M"))
    
    def get_selected_time_range(self):
        """Получение выбранного временного диапазона"""
        try:
            # Получаем дату и время начала
            start_date_str = self.start_date.get()
            start_hour = int(self.start_hour.get())
            start_minute = int(self.start_minute.get())
            start_dt = datetime.strptime(start_date_str, "%d.%m.%Y")
            start_dt = start_dt.replace(hour=start_hour, minute=start_minute)
            
            # Получаем дату и время окончания
            end_date_str = self.end_date.get()
            end_hour = int(self.end_hour.get())
            end_minute = int(self.end_minute.get())
            end_dt = datetime.strptime(end_date_str, "%d.%m.%Y")
            end_dt = end_dt.replace(hour=end_hour, minute=end_minute)
            
            return start_dt, end_dt
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный формат даты или времени")
            return None, None
    
    def fill_alert_info(self):
        """Заполнение информации об алерте"""
        for item in self.alert_info_tree.get_children():
            self.alert_info_tree.delete(item)
        
        labels = self.alert_data.get('labels', {})
        annotations = self.alert_data.get('annotations', {})
        
        info_data = [
            ("Название алерта", labels.get('alertname', 'N/A')),
            ("Серьезность", labels.get('severity', 'N/A')),
            ("Окружение", labels.get('env', 'N/A')),
            ("Пространство имен", labels.get('namespace', 'N/A')),
            ("Сервис", labels.get('service', 'N/A')),
            ("URL", labels.get('url', 'N/A')),
            ("Описание", annotations.get('description', 'N/A')),
            ("Состояние", self.alert_data.get('state', 'N/A')),
            ("Активен с", self.alert_data.get('activeAt', self.alert_data.get('startsAt', 'N/A'))),
            ("Значение", self.alert_data.get('value', 'N/A')),
            ("Generator URL", self.alert_data.get('generatorURL', 'N/A'))
        ]
        
        for key, value in info_data:
            self.alert_info_tree.insert("", "end", values=(key, value))
    
    def plot_alert_metric(self):
        """Построение графика метрики для алерта"""
        try:
            self.status_var.set(f"Сервер: {self.selected_server} | Получение данных...")
            self.window.update_idletasks()
            
            # Получаем выбранный временной диапазон
            start_dt, end_dt = self.get_selected_time_range()
            if start_dt is None or end_dt is None:
                return
                
            # Получаем сырые данные
            raw_data, expr = self.data_fetcher.get_metric_data(
                self.alert_data,
                start_dt,
                end_dt,
                self.step_var.get()
            )
            
            # Обновляем поле с выражением
            self.expr_text.config(state=tk.NORMAL)
            self.expr_text.delete(1.0, tk.END)
            self.expr_text.insert(tk.END, expr)
            self.expr_text.config(state=tk.DISABLED)
            
            # Обрабатываем данные и строим график
            self.plot_builder = PlotBuilder(self.figure, self.alert_data)
            df = self.plot_builder.process_data(raw_data)
            self.current_data = df
            
            self.status_var.set(f"Сервер: {self.selected_server} | Построение графика...")
            self.window.update_idletasks()
            
            _, series_count, total_series = self.plot_builder.build_plot(expr)
            
            # Обновляем статус
            status_msg = f"Сервер: {self.selected_server} | Отображено {series_count} из {total_series} рядов"
            if total_series > series_count:
                status_msg += " (только первые 15)"
                
            self.status_var.set(status_msg)
            self.canvas.draw()
            
        except Exception as e:
            self.status_var.set(f"Сервер: {self.selected_server} | Ошибка: {str(e)}")
            self.plot.clear()
            self.plot.text(0.5, 0.5, f"Ошибка:\n{str(e)}", 
                          horizontalalignment='center', verticalalignment='center',
                          transform=self.plot.transAxes, fontsize=10)
            self.canvas.draw()
            logging.error(f"Ошибка построения графика: {str(e)}")
    
    def edit_expression(self):
        """Редактирование выражения метрики"""
        alert_name = self.alert_data.get('labels', {}).get('alertname')
        if not alert_name:
            messagebox.showerror("Ошибка", "Не удалось определить имя алерта")
            return
        
        # Получаем текущее выражение
        current_expr = self.expr_text.get(1.0, tk.END).strip()
        
        # Открываем диалог редактирования
        new_expr = simpledialog.askstring(
            "Редактирование функции", 
            "Введите новое выражение для метрики:",
            initialvalue=current_expr,
            parent=self.window
        )
        
        if new_expr:
            # Сохраняем в конфиг
            self.data_fetcher.config_manager.set_expression(alert_name, new_expr)
            
            # Обновляем поле с выражением
            self.expr_text.config(state=tk.NORMAL)
            self.expr_text.delete(1.0, tk.END)
            self.expr_text.insert(tk.END, new_expr)
            self.expr_text.config(state=tk.DISABLED)
            
            # Перестраиваем график
            self.plot_alert_metric()
    
    def export_to_csv(self):
        """Экспорт данных в CSV формате"""
        if self.current_data is None or self.plot_builder is None:
            messagebox.showerror("Ошибка", "Нет данных для экспорта")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Сохранить данные как"
        )
        
        if not file_path:
            return
            
        try:
            self.plot_builder.export_to_csv(file_path)
            messagebox.showinfo("Успех", f"Данные успешно экспортированы в:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные:\n{str(e)}")
    
    def open_in_prometheus(self):
        """Открытие графика в веб-интерфейсе Prometheus"""
        # Пытаемся получить выражение
        expr = self.expr_text.get(1.0, tk.END).strip()
        
        # Получаем выбранный временной диапазон
        start_dt, end_dt = self.get_selected_time_range()
        if start_dt is None or end_dt is None:
            return
            
        # Рассчитываем диапазон в часах
        time_delta = end_dt - start_dt
        hours = int(time_delta.total_seconds() / 3600)
        range_str = f"{hours}h"
        
        # Формируем URL
        encoded_expr = quote(expr, safe='')
        prom_url = (
            f"{self.data_fetcher.get_prometheus_url()}/graph?g0.expr={encoded_expr}"
            f"&g0.tab=1&g0.stacked=0&g0.show_exemplars=0"
            f"&g0.range_input={range_str}&g0.step={self.step_var.get()}"
        )
        
        # Открываем в браузере
        webbrowser.open(prom_url)
        self.status_var.set(f"Сервер: {self.selected_server} | Открыто в Prometheus: {prom_url[:100]}...")


class PrometheusAlertsApp:
    def __init__(self, parent):
        self.parent = parent
        self.window = ttk.Frame(parent)
        self.window.pack(fill=tk.BOTH, expand=True)
        
        # Менеджер серверов
        self.server_manager = ServerManager()
        self.selected_server = "Все серверы"
        self.current_alert = None
        self.all_alerts = []
        self.service_counter = ServiceAlertCounter(self.server_manager)  # Новый экземпляр счетчика сервисов
        
        # Основные элементы интерфейса
        self.create_widgets()
        self.load_all_alerts()
    
    def create_widgets(self):
        """Создание элементов интерфейса"""
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Фрейм для поиска алертов
        search_frame = ttk.LabelFrame(main_frame, text="Поиск алертов")
        search_frame.pack(fill=tk.X, pady=5)
        
        # Выбор сервера
        ttk.Label(search_frame, text="Сервер:").pack(side=tk.LEFT, padx=5)
        
        # Фрейм для кнопки выбора сервера
        server_menu_frame = ttk.Frame(search_frame)
        server_menu_frame.pack(side=tk.LEFT, padx=5)
        
        # Кнопка для открытия меню серверов
        self.server_var = tk.StringVar(value=self.selected_server)
        self.server_menu_btn = ttk.Button(
            server_menu_frame,
            textvariable=self.server_var,
            width=25,
            command=self.show_server_menu
        )
        self.server_menu_btn.pack(fill=tk.X, expand=True)
        
        # Кнопка для статистики сервисов
        self.service_stats_btn = ttk.Button(
            search_frame,
            text="Статистика сервисов",
            command=self.show_service_alerts_stats,
            width=20
        )
        self.service_stats_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind('<KeyRelease>', self.filter_alerts)
        
        # Кнопка обновления алертов
        self.refresh_button = ttk.Button(search_frame, text="Обновить", command=self.load_all_alerts)
        self.refresh_button.pack(side=tk.RIGHT, padx=5)
        
        # Фрейм для выбора алерта
        alert_frame = ttk.LabelFrame(main_frame, text="Доступные алерты")
        alert_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Treeview для отображения алертов
        columns = ("name", "severity", "env", "namespace", "service", "state", "active_since", "value")
        self.alerts_tree = ttk.Treeview(alert_frame, columns=columns, show="headings")
        
        # Настройка колонок
        self.alerts_tree.heading("name", text="Название алерта")
        self.alerts_tree.heading("severity", text="Серьезность")
        self.alerts_tree.heading("env", text="Окружение")
        self.alerts_tree.heading("namespace", text="Пространство имен")
        self.alerts_tree.heading("service", text="Сервис")
        self.alerts_tree.heading("state", text="Состояние")
        self.alerts_tree.heading("active_since", text="Активен с")
        self.alerts_tree.heading("value", text="Значение")
        
        # Устанавливаем ширину колонок
        self.alerts_tree.column("name", width=200)
        self.alerts_tree.column("severity", width=100)
        self.alerts_tree.column("env", width=100)
        self.alerts_tree.column("namespace", width=150)
        self.alerts_tree.column("service", width=150)
        self.alerts_tree.column("state", width=80)
        self.alerts_tree.column("active_since", width=180)
        self.alerts_tree.column("value", width=100)
        
        # Добавляем скроллбар
        scrollbar = ttk.Scrollbar(alert_frame, orient="vertical", command=self.alerts_tree.yview)
        self.alerts_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.alerts_tree.pack(fill=tk.BOTH, expand=True)
        
        # Привязка события выбора
        self.alerts_tree.bind("<<TreeviewSelect>>", self.on_alert_selected)
        
        # Контекстное меню для алертов
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="Показать график метрики", command=self.show_metric_graph)
        self.context_menu.add_command(label="Открыть в Prometheus", command=self.open_alert_in_prometheus)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Статистика алертов по сервисам", command=self.show_service_alerts_stats)
        self.alerts_tree.bind("<Button-3>", self.show_context_menu)
        
        # Фрейм для отображения информации об алерте
        info_frame = ttk.LabelFrame(main_frame, text="Детали алерта")
        info_frame.pack(fill=tk.X, pady=5)
        
        # Таблица с лейблами алерта
        columns = ("label", "value")
        self.labels_tree = ttk.Treeview(info_frame, columns=columns, show="headings", height=4)
        self.labels_tree.heading("label", text="Label")
        self.labels_tree.heading("value", text="Value")
        self.labels_tree.column("label", width=150)
        self.labels_tree.column("value", width=300)
        self.labels_tree.pack(fill=tk.X, padx=5, pady=5)
        
        # Аннотации алерта
        self.annotation_text = scrolledtext.ScrolledText(info_frame, height=4, wrap=tk.WORD)
        self.annotation_text.pack(fill=tk.X, padx=5, pady=5)
        self.annotation_text.insert(tk.END, "Аннотации появятся здесь...")
        self.annotation_text.config(state=tk.DISABLED)
        
        # Статус бар
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.window, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var.set(f"Сервер: {self.selected_server} | Готово")

    def show_extended_stats_for_selected(self, tree):
        """Показывает расширенную статистику для выбранного сервиса"""
        selected_items = tree.selection()
        if not selected_items:
            return
            
        selected_item = selected_items[0]
        service_name = tree.item(selected_item, 'values')[0]
        self.service_counter.show_extended_service_stats(service_name)

    def show_service_alerts_stats(self):
        """Показывает статистику алертов по сервисам"""
        try:
            self.status_var.set("Получение статистики алертов по сервисам...")
            self.window.update_idletasks()
            
            service_counts = self.service_counter.get_service_alerts_count()
            if not service_counts:
                messagebox.showinfo("Информация", "Нет данных о алертах по сервисам")
                return
            
            # Создаем окно для отображения статистики
            stats_window = tk.Toplevel(self.window)
            stats_window.title("Статистика алертов по сервисам (за 24 часа)")
            stats_window.geometry("500x700")
            
            # Основной фрейм
            main_frame = ttk.Frame(stats_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Заголовок
            ttk.Label(
                main_frame, 
                text="Количество алертов по сервисам за последние 24 часа",
                font=("Arial", 10, "bold")
            ).pack(pady=5)
            
            # Treeview для отображения данных
            tree_frame = ttk.Frame(main_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True)
            
            columns = ("service", "count")
            tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
            
            # Настройка колонок
            tree.heading("service", text="Сервис")
            tree.heading("count", text="Кол-во алертов")
            tree.column("service", width=350, anchor=tk.W)
            tree.column("count", width=100, anchor=tk.CENTER)
            
            # Полоса прокрутки
            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Заполняем данными
            for service, count in service_counts:
                tree.insert("", tk.END, values=(service, count))
            
            # Контекстное меню для построения графика
            context_menu = tk.Menu(stats_window, tearoff=0)
            context_menu.add_command(
                label="Построить график алертов", 
                command=lambda: self.show_service_graph_for_selected(tree)
            )
            
            tree.bind("<Button-3>", lambda e: context_menu.post(e.x_root, e.y_root))

            context_menu = tk.Menu(stats_window, tearoff=0)
            context_menu.add_command(
                label="Построить график алертов", 
                command=lambda: self.show_service_graph_for_selected(tree)
            )
            # Добавляем новую команду
            context_menu.add_command(
                label="Расширенная статистика", 
                command=lambda: self.show_extended_stats_for_selected(tree)
            )

            tree.bind("<Button-3>", lambda e: context_menu.post(e.x_root, e.y_root))
            
            # Кнопка обновления
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill=tk.X, pady=5)
            
            ttk.Button(
                btn_frame,
                text="Обновить данные",
                command=lambda: self.update_service_stats(tree)
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                btn_frame,
                text="Закрыть",
                command=stats_window.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
            self.status_var.set(f"Сервер: {self.selected_server} | Готово")
            
        except Exception as e:
            self.status_var.set(f"Ошибка: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось получить статистику: {str(e)}")

    def show_service_graph_for_selected(self, tree):
        """Показывает график для выбранного сервиса"""
        selected_items = tree.selection()
        if not selected_items:
            return
            
        selected_item = selected_items[0]
        service_name = tree.item(selected_item, 'values')[0]
        self.service_counter.show_service_graph(service_name)


    def update_service_stats(self, tree):
        """Обновляет данные в окне статистики сервисов"""
        try:
            for item in tree.get_children():
                tree.delete(item)
                
            service_counts = self.service_counter.get_service_alerts_count()
            if service_counts:
                for service, count in service_counts:
                    tree.insert("", tk.END, values=(service, count))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить данные: {str(e)}")
    
    def show_server_menu(self):
        """Показывает меню с доступными серверами"""
        # Создаем новое меню
        menu = tk.Menu(self.window, tearoff=0)
        
        # Добавляем пункты меню для каждого сервера
        for server_name in self.server_manager.get_server_names():
            menu.add_command(
                label=server_name,
                command=lambda name=server_name: self.set_server(name)
            )
        
        try:
            # Показываем меню под кнопкой
            x = self.server_menu_btn.winfo_rootx()
            y = self.server_menu_btn.winfo_rooty() + self.server_menu_btn.winfo_height()
            menu.post(x, y)
            
            # Закрываем меню при потере фокуса
            menu.bind("<FocusOut>", lambda e: menu.destroy())
        except tk.TclError:
            menu.destroy()
    
    def set_server(self, server_name):
        """Устанавливает выбранный сервер"""
        self.server_var.set(server_name)
        self.selected_server = server_name
        self.status_var.set(f"Сервер: {self.selected_server} | Загрузка алертов...")
        self.window.update_idletasks()
        self.load_all_alerts()
    
    def load_all_alerts(self):
        """Загрузка всех алертов из Prometheus"""
        try:
            self.status_var.set(f"Сервер: {self.selected_server} | Загрузка алертов...")
            self.window.update_idletasks()
            
            # Определяем сервер для запроса
            server_url = self.server_manager.get_server_url(self.selected_server)
            if not server_url and self.selected_server != "Все серверы":
                messagebox.showerror("Ошибка", "Неверно настроен сервер")
                return
                
            # Для режима "Все серверы" делаем несколько запросов
            alerts = []
            if self.selected_server == "Все серверы":
                for name, url in self.server_manager.servers.items():
                    try:
                        server_alerts = self.fetch_alerts_from_server(url)
                        # Добавляем имя сервера в метки для идентификации
                        for alert in server_alerts:
                            alert['server'] = name
                        alerts.extend(server_alerts)
                    except Exception as e:
                        logging.error(f"Ошибка загрузки с сервера {name}: {str(e)}")
            else:
                alerts = self.fetch_alerts_from_server(server_url)
            
            # Очищаем Treeview
            for item in self.alerts_tree.get_children():
                self.alerts_tree.delete(item)
            
            # Сохраняем все алерты для фильтрации
            self.all_alerts = []
            
            # Заполняем Treeview
            for alert in alerts:
                labels = alert.get('labels', {})
                name = labels.get('alertname', 'Unknown Alert')
                severity = labels.get('severity', '')
                env = labels.get('env', '')
                namespace = labels.get('namespace', '')
                service = labels.get('service', '')
                state = alert.get('state', 'unknown')
                active_since = alert.get('activeAt', alert.get('startsAt', ''))
                value = alert.get('value', '')
                
                display_data = (name, severity, env, namespace, service, state, active_since, value)
                self.all_alerts.append((display_data, alert))
                self.alerts_tree.insert("", "end", values=display_data)
            
            self.status_var.set(f"Сервер: {self.selected_server} | Загружено {len(alerts)} алертов")
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить алерты:\n{str(e)}")
            self.status_var.set(f"Сервер: {self.selected_server} | Ошибка загрузки алертов: {str(e)}")
    
    def fetch_alerts_from_server(self, server_url):
        """Загрузка алертов с конкретного сервера с оптимизированной пагинацией"""
        try:
            all_alerts = []
            page = 1
            max_pages = 10  # Защита от бесконечного цикла
            is_prom_ld_001 = "prom-ld-001:9093" in server_url
            
            while page <= max_pages:
                try:
                    params = {
                        'active': True,
                        'silenced': False,
                        'inhibited': False,
                        'page': page
                    }
                    # Уменьшаем таймаут для отдельных страниц
                    response = requests.get(f'{server_url}/api/v1/alerts', 
                                        params=params, 
                                        timeout=5)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data['status'] != 'success':
                        error_msg = data.get('error', 'Unknown error')
                        raise Exception(f"Prometheus API error: {error_msg}")
                    
                    alerts = data['data']['alerts']
                    if not alerts:
                        break  # Нет данных на странице - завершаем
                    
                    # Фильтрация только если это prom-ld-001
                    if is_prom_ld_001:
                        alerts = [alert for alert in alerts 
                                if 'omni' in alert.get('labels', {}).get('alertname', '').lower()]
                    
                    all_alerts.extend(alerts)
                    
                    # Оптимизация: прекращаем если получено меньше алертов, чем ожидается на странице
                    if len(alerts) < 50:  # Предполагаем, что полная страница содержит 50+ алертов
                        break
                        
                    page += 1
                    
                except requests.exceptions.Timeout:
                    logging.warning(f"Timeout при загрузке страницы {page} с {server_url}")
                    break  # Прекращаем при таймауте
                except requests.exceptions.RequestException as e:
                    logging.error(f"Ошибка сети при загрузке страницы {page}: {str(e)}")
                    break
                
            return all_alerts
            
        except Exception as e:
            logging.error(f"Критическая ошибка загрузки с {server_url}: {str(e)}")
            return []
    
    def filter_alerts(self, event=None):
        """Фильтрация алертов по введенному тексту"""
        search_text = self.search_var.get().lower()
        
        for item in self.alerts_tree.get_children():
            self.alerts_tree.delete(item)
        
        for display_data, alert in self.all_alerts:
            if any(search_text in str(value).lower() for value in display_data):
                self.alerts_tree.insert("", "end", values=display_data)
    
    def on_alert_selected(self, event):
        """Обработка выбора алерта в Treeview"""
        selected_item = self.alerts_tree.selection()
        if not selected_item:
            return
            
        item_values = self.alerts_tree.item(selected_item[0], 'values')
        
        for display_data, alert in self.all_alerts:
            if tuple(display_data) == item_values:
                self.current_alert = alert
                self.display_alert_info(alert)
                break
    
    def display_alert_info(self, alert):
        """Отображение информации о выбранном алерте"""
        # Лейблы алерта
        for item in self.labels_tree.get_children():
            self.labels_tree.delete(item)
        
        labels = alert.get('labels', {})
        for key, value in labels.items():
            self.labels_tree.insert("", "end", values=(key, value))
        
        # Аннотации алерта
        self.annotation_text.config(state=tk.NORMAL)
        self.annotation_text.delete(1.0, tk.END)
        
        annotations = alert.get('annotations', {})
        if annotations:
            for key, value in annotations.items():
                self.annotation_text.insert(tk.END, f"{key}: {value}\n")
        
        generator_url = alert.get('generatorURL', '')
        if generator_url:
            self.annotation_text.insert(tk.END, f"\ngeneratorURL: {generator_url}")
        
        # Добавляем информацию о сервере для алертов из режима "Все серверы"
        if 'server' in alert:
            self.annotation_text.insert(tk.END, f"\n\nСервер: {alert['server']}")
        
        if not self.annotation_text.get(1.0, tk.END).strip():
            self.annotation_text.insert(tk.END, "Нет аннотаций")
        
        self.annotation_text.config(state=tk.DISABLED)
    
    def show_context_menu(self, event):
        """Показ контекстного меню"""
        item = self.alerts_tree.identify_row(event.y)
        if item:
            self.alerts_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def show_metric_graph(self):
        """Показ графика метрики в отдельном окне"""
        if not self.current_alert:
            messagebox.showwarning("Предупреждение", "Алерт не выбран")
            return
            
        # Для алертов из режима "Все серверы" используем сервер из меток
        server = self.selected_server
        if 'server' in self.current_alert:
            server = self.current_alert['server']
            
        AlertGraphWindow(self.window, self.server_manager, server, self.current_alert)
    
    def open_alert_in_prometheus(self):
        """Открытие выбранного алерта в веб-интерфейсе Prometheus"""
        if not self.current_alert:
            messagebox.showwarning("Предупреждение", "Алерт не выбран")
            return
        
        # Определяем сервер для открытия
        server = self.selected_server
        if 'server' in self.current_alert:
            server = self.current_alert['server']
            
        server_url = self.server_manager.get_server_url(server)
        if not server_url:
            messagebox.showerror("Ошибка", "Не удалось определить URL сервера")
            return
        
        alert_name = self.current_alert.get('labels', {}).get('alertname')
        if not alert_name:
            messagebox.showerror("Ошибка", "Не удалось определить имя алерта")
            return
        
        # Пытаемся получить выражение
        fetcher = DataFetcher(self.server_manager, server)
        expr = fetcher.config_manager.get_expression(alert_name)
        
        if not expr:
            expr = fetcher.fetch_alert_expression(alert_name)
        
        if not expr:
            expr = fetcher.extract_expr_from_url(
                self.current_alert.get('generatorURL', '')
            )
        
        if not expr:
            messagebox.showerror("Ошибка", "Не удалось извлечь выражение метрики")
            return
        
        # Формируем URL
        encoded_expr = quote(expr, safe='')
        prom_url = (
            f"{server_url}/graph?g0.expr={encoded_expr}"
            f"&g0.tab=1&g0.stacked=0&g0.show_exemplars=0"
            f"&g0.range_input=1h&g0.step=1m"
        )
        
        # Открываем в браузере
        webbrowser.open(prom_url)
        self.status_var.set(f"Сервер: {server} | Открыто в Prometheus: {prom_url[:100]}...")


class ServiceAlertCounter:
    """Класс для подсчета алертов по сервисам"""
    def __init__(self, server_manager):
        self.server_manager = server_manager
        self.endpoint = "http://omni.prometheus-prod.kifr-ru.local/"
        self.logger = logging.getLogger(__name__)

    def get_service_alerts_count(self):
        """Получает количество алертов по сервисам за последние 24 часа"""
        try:
            query = 'count by (service) (count_over_time(ALERTS{alertstate="firing"}[24h] offset 24h))'
            url = f"{self.endpoint}/api/v1/query"
            params = {'query': query}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                raise Exception(f"Prometheus API error: {data.get('error', 'Unknown error')}")
            
            results = data['data']['result']
            service_counts = []
            
            for result in results:
                service = result['metric'].get('service', 'unknown')
                count = int(result['value'][1])
                service_counts.append((service, count))
            
            # Сортируем по убыванию количества алертов
            service_counts.sort(key=lambda x: x[1], reverse=True)
            return service_counts
            
        except Exception as e:
            self.logger.error(f"Ошибка получения количества алертов по сервисам: {str(e)}")
            return None
        
    def get_extended_service_alerts_count(self):
        """Получает расширенную статистику алертов с детализацией по кодам, сообщениям и route"""
        try:
            query = (
                'count by (service, route, result_code, result_message) ('
                'count_over_time(ALERTS{alertstate="firing"}[24h] offset 24h'
                '))'
            )
            url = f"{self.endpoint}/api/v1/query"
            params = {'query': query}
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] != 'success':
                raise Exception(f"Prometheus API error: {data.get('error', 'Unknown error')}")
            
            results = data['data']['result']
            extended_counts = []
            
            for result in results:
                service = result['metric'].get('service', 'unknown')
                route = result['metric'].get('route', 'N/A')  # Добавляем route
                result_code = result['metric'].get('result_code', 'N/A')
                result_message = result['metric'].get('result_message', 'N/A')
                count = int(result['value'][1])
                extended_counts.append((service, route, result_code, result_message, count))
            
            # Сортируем по сервису и количеству алертов
            extended_counts.sort(key=lambda x: (x[0], -x[4]))
            return extended_counts
            
        except Exception as e:
            self.logger.error(f"Ошибка получения расширенной статистики алертов: {str(e)}")
            return None
        
    def show_extended_service_stats(self, service_name):
        """Показывает расширенную статистику для конкретного сервиса"""
        try:
            # Получаем расширенную статистику
            extended_stats = self.get_extended_service_alerts_count()
            if not extended_stats:
                messagebox.showinfo("Информация", f"Нет данных для сервиса '{service_name}'")
                return
            
            # Фильтруем по выбранному сервису
            service_stats = [s for s in extended_stats if s[0] == service_name]
            if not service_stats:
                messagebox.showinfo("Информация", f"Нет данных для сервиса '{service_name}'")
                return
            
            # Создаем окно для отображения статистики
            stats_window = tk.Toplevel()
            stats_window.title(f"Расширенная статистика: {service_name}")
            stats_window.geometry("1200x600")  # Увеличиваем размер окна для отображения route
            
            # Основной фрейм
            main_frame = ttk.Frame(stats_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Таблица с детализацией
            tree_frame = ttk.Frame(main_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Добавляем колонку для route
            columns = ("route", "result_code", "result_message", "count")
            tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
            
            # Настройка колонок
            tree.heading("route", text="Эндпоинт")
            tree.heading("result_code", text="Код результата")
            tree.heading("result_message", text="Сообщение")
            tree.heading("count", text="Количество алертов")
            tree.column("route", width=250, anchor=tk.W)
            tree.column("result_code", width=150, anchor=tk.W)
            tree.column("result_message", width=400, anchor=tk.W)
            tree.column("count", width=100, anchor=tk.CENTER)
            
            # Полоса прокрутки
            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Заполняем данными
            total_alerts = 0
            for stat in service_stats:
                _, route, code, message, count = stat
                tree.insert("", tk.END, values=(route, code, message, count))
                total_alerts += count
            
            # График распределения
            graph_frame = ttk.LabelFrame(main_frame, text=f"Распределение алертов ({total_alerts} всего)")
            graph_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            
            fig = Figure(figsize=(8, 4), dpi=100)
            ax = fig.add_subplot(111)
            
            # Подготовка данных для графика
            # Группируем по route, result_code и result_message для отображения на графике
            labels = [f"{s[1]}: {s[2]} - {s[3]}" for s in service_stats]
            counts = [s[4] for s in service_stats]
            
            # Строим pie chart
            ax.pie(
                counts,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                textprops={'fontsize': 6}  # Уменьшаем размер шрифта для лучшего отображения
            )
            ax.axis('equal')  # Круговая диаграмма
            ax.set_title(f"Распределение алертов: {service_name}", fontsize=10)
            
            # Встраиваем график в окно
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Кнопка экспорта
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill=tk.X, pady=5)
            
            ttk.Button(
                btn_frame,
                text="Экспорт в CSV",
                command=lambda: self.export_extended_stats(service_stats, service_name)
            ).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось показать статистику: {str(e)}")
    
    def export_extended_stats(self, data, service_name):
        """Экспортирует расширенную статистику в CSV"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Сохранить статистику как",
                initialfile=f"{service_name}_alerts_stats.csv"
            )
            
            if not file_path:
                return
                
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Сервис", "Эндпоинт", "Код результата", "Сообщение", "Количество алертов"])
                for row in data:
                    writer.writerow(row)
                    
            messagebox.showinfo("Успех", f"Данные экспортированы в:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта: {str(e)}")

    def show_service_graph(self, service_name):
        """Показывает график алертов для конкретного сервиса"""
        try:
            # Формируем запрос для конкретного сервиса
            query = f'count by (service) (count_over_time(ALERTS{{alertstate="firing", service="{service_name}"}}[24h] offset 24h))'
            
            # Создаем окно для графика
            window = tk.Toplevel()
            window.title(f"Алерты сервиса: {service_name}")
            window.geometry("1000x600")
            
            # Создаем фигуру и холст для графика
            figure = Figure(figsize=(10, 5), dpi=100)
            plot = figure.add_subplot(111)
            canvas = FigureCanvasTkAgg(figure, master=window)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Выполняем запрос
            start = datetime.now() - timedelta(hours=48)  # 48 часов чтобы охватить offset 24h
            end = datetime.now() - timedelta(hours=24)
            step = "1h"
            
            data_fetcher = DataFetcher(self.server_manager, "Server OMNI metrics")
            raw_data, _ = data_fetcher.get_metric_data(
                {'labels': {}, 'annotations': {}}, 
                start, 
                end, 
                step,
                custom_query=query  # Используем кастомный запрос
            )
            
            # Обрабатываем данные
            plot_builder = PlotBuilder(figure, {})
            df = plot_builder.process_data(raw_data)
            
            # Строим график
            plot_builder.build_plot(query)
            canvas.draw()
            
            # Добавляем заголовок
            plot.set_title(f"Алерты сервиса: {service_name} за 24 часа", fontsize=12)
            plot.set_xlabel("Время", fontsize=10)
            plot.set_ylabel("Количество алертов", fontsize=10)
            canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось построить график: {str(e)}")