import json
import requests
import tkinter as tk
from tkinter import Widget, ttk, messagebox, scrolledtext
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Вывод в консоль
        logging.FileHandler('api_requests.log')  # Запись в файл
    ]
)
logger = logging.getLogger(__name__)

class ApiMethod(ABC):
    """Абстрактный базовый класс для методов API"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.param_widgets = {}
    
    @abstractmethod
    def create_ui(self, parent) -> None:
        """Создание UI для метода"""
        pass
    
    @abstractmethod
    def execute(self) -> Optional[requests.Response]:
        """Выполнение запроса"""
        pass
    
    def log_request(self, method: str, url: str, headers: Dict[str, str], params: Dict[str, Any] = None, data: Any = None):
        """Логирование информации о запросе"""
        logger.info(f"=== REQUEST ===")
        logger.info(f"Method: {method}")
        logger.info(f"URL: {url}")
        
        if params:
            logger.info(f"Params: {params}")
        
        logger.info("Headers:")
        for key, value in headers.items():
            logger.info(f"  {key}: {value}")
        
        if data:
            logger.info("Body:")
            if isinstance(data, dict):
                logger.info(f"  {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                logger.info(f"  {data}")
    
    def log_response(self, response: requests.Response):
        """Логирование информации о ответе"""
        logger.info(f"=== RESPONSE ===")
        logger.info(f"Status: {response.status_code}")
        
        logger.info("Headers:")
        for key, value in response.headers.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("Body:")
        try:
            response_data = response.json()
            logger.info(f"  {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            logger.info(f"  {response.text}")
    
    def validate_parameters(self) -> bool:
        """Проверка обязательных параметров"""
        missing_params = []
        for param, config in self.config.get("params", {}).items():
            if config.get("required", False):
                widget = self.param_widgets.get(param)
                if widget:
                    if isinstance(widget, tk.Entry):
                        value = widget.get()
                    elif isinstance(widget, (tk.StringVar, tk.BooleanVar)):
                        value = widget.get()
                    else:
                        value = str(widget.get())
                    
                    if not value:
                        missing_params.append(param)
        
        if missing_params:
            messagebox.showwarning(
                "Ошибка",
                f"Не заполнены обязательные параметры:\n{', '.join(missing_params)}"
            )
            return False
        return True

class StandardApiMethod(ApiMethod):
    """Стандартный метод API с параметрами"""
    
    def create_ui(self, parent) -> None:
        """Создание UI для стандартного метода"""
        for widget in parent.winfo_children():
            widget.destroy()
        
        if "params" not in self.config:
            return
            
        for row, (param, config) in enumerate(self.config["params"].items()):
            label_text = f"{param}:" + (" *" if config.get("required", False) else "")
            ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
            
            if config["type"] == "entry":
                entry = self._create_entry_widget(parent, config)
                entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=2)
                self.param_widgets[param] = entry
            
            elif config["type"] == "combobox":
                var = tk.StringVar(value=config.get("default", ""))
                cb = ttk.Combobox(
                    parent,
                    textvariable=var,
                    values=config["values"],
                    state="readonly",
                    width=37
                )
                cb.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
                self.param_widgets[param] = var
            
            elif config["type"] == "check":
                var = tk.BooleanVar(value=config.get("default", False))
                cb = ttk.Checkbutton(parent, variable=var, text="")
                cb.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
                self.param_widgets[param] = var
        
        # Добавляем комбобокс для типа остатков только для метода "Запрос остатков ИМ"
        if self.name == "Запрос остатков ИМ":
            row += 1
            ttk.Label(parent, text="Тип остатка (exclusion):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
            
            stock_type_var = tk.StringVar(value="-")
            stock_type_cb = ttk.Combobox(
                parent,
                textvariable=stock_type_var,
                values=["-", "PICKUP", "DISTRIBUTION_CENTER", "MARKETPLACE", "MARKETPLACE_RAW", 
                       "STOCK", "RAW", "SHOWROOM", "VENDOR", "PURCHASE_ORDER"],
                state="readonly",
                width=37
            )
            stock_type_cb.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
            self.param_widgets["stockType"] = stock_type_var
            
            # Добавляем подсказку о возможности ввода нескольких ID
            row += 1
            info_label = ttk.Label(
                parent, 
                text="Для ввода нескольких номенклатур укажите ID через запятую",
                foreground="blue",
                font=('Arial', 9)
            )
            info_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        parent.columnconfigure(1, weight=1)
    
    def execute(self) -> Optional[requests.Response]:
        """Выполнение запроса"""
        if not self.validate_parameters():
            return None
        
        try:
            url = self.config["url"]
            headers = self.config["headers"].copy()
            
            # Подготавливаем параметры запроса и заголовки отдельно
            request_params = {}
            for param, widget in self.param_widgets.items():
                if isinstance(widget, tk.Entry):
                    value = widget.get()
                elif isinstance(widget, tk.BooleanVar):
                    value = widget.get()
                elif isinstance(widget, tk.StringVar):
                    value = widget.get()
                else:
                    value = str(widget.get())
                
                # Сохраняем значение для использования в теле запроса
                request_params[param] = value
                
                # Добавляем только те параметры, которые должны быть в заголовках
                # И только строковые значения (не булевы)
                if param in self.config.get("params", {}):
                    if isinstance(value, bool):
                        # Пропускаем булевы значения - они не должны быть в заголовках
                        continue
                    if param == "Authorization" and not value.startswith("Bearer "):
                        value = f"Bearer {value}"
                    headers[param] = str(value)  # Преобразуем в строку

            # Подготавливаем тело запроса
            request_body = {}
            
            # Обрабатываем productId - разделяем по запятой если нужно
            if "productId" in request_params:
                product_ids = [pid.strip() for pid in request_params["productId"].split(",") if pid.strip()]
                request_body["products"] = [{"productId": pid} for pid in product_ids]
            
            if "isMinPriority" in request_params:
                # Преобразуем значение чекбокса в булево
                is_min_priority = request_params["isMinPriority"]
                if isinstance(is_min_priority, str):
                    is_min_priority = is_min_priority.lower() == "true"
                request_body["isMinPriority"] = is_min_priority
            
            # Добавляем exclusion если выбран тип остатка (не "-")
            if "stockType" in request_params and request_params["stockType"] != "-":
                request_body["exclusion"] = {
                    "stockTypes": [request_params["stockType"]]
                }

            # Логируем запрос
            self.log_request(self.config["method"], url, headers, data=request_body)
            
            # Выполняем запрос
            response = requests.request(
                method=self.config["method"],
                url=url,
                headers=headers,
                json=request_body,
                timeout=30
            )
            
            # Логируем ответ
            self.log_response(response)
            
            response.raise_for_status()
            
            return response

        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка запроса: {str(e)}"
            messagebox.showerror("Ошибка сети", error_msg)
            return None
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неожиданная ошибка: {str(e)}")
            return None
    
    def _create_entry_widget(self, parent, config):
        """Создание поля ввода"""
        entry = ttk.Entry(
            parent,
            width=config.get("width", 40),
            show="*" if config.get("sensitive", False) else None
        )
        return entry

class CalculationApiMethod(ApiMethod):
    """Метод для пересчета остатков"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.last_response_timestamp = None
    
    def create_ui(self, parent) -> None:
        """Создание UI для метода пересчета остатков"""
        for widget in parent.winfo_children():
            widget.destroy()
        
        # Поле для ввода productIds
        ttk.Label(parent, text="Номенклатуры (если несколько, то через запятую):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        product_ids_entry = ttk.Entry(parent, width=50)
        product_ids_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.param_widgets["productIds"] = product_ids_entry
        
        # Тип остатков
        ttk.Label(parent, text="Тип остатков:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        
        remain_type_var = tk.StringVar(value="STOCK")
        remain_type_cb = ttk.Combobox(
            parent,
            textvariable=remain_type_var,
            values=["PICKUP","DISTRIBUTION_CENTER","MARKETPLACE","MARKETPLACE_RAW","STOCK","PICKUP","RAW","SHOWROOM","VENDOR","PURCHASE_ORDER"],
            state="readonly",
            width=20
        )
        remain_type_cb.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        self.param_widgets["remainType"] = remain_type_var
        
        # Информационное сообщение
        info_label = ttk.Label(
            parent, 
            text="Внимание: "
            "\n[Асинхронно] Если не передан productIds, то будет выполнен расчёт по всей базе товаров (inventory)."
            "\n[Синхронно] Иначе считается по переданным productIds в разрезе remainType.",
            foreground="red",
            font=('Arial', 9, 'bold')
        )
        info_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10)
        
        # Кнопка для просмотра логов (изначально скрыта)
        self.view_logs_button = ttk.Button(
            parent,
            text="Просмотр логов в ELK",
            command=self.open_elk_logs,
            state="disabled"
        )
        self.view_logs_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        parent.columnconfigure(1, weight=1)
    
    def validate_product_ids(self, product_ids_str: str) -> Tuple[bool, List[str]]:
        """Проверка корректности введенных номенклатуры"""
        if not product_ids_str.strip():
            return True, []  # Пустая строка - пересчет всей базы
        
        # Разделяем по запятым и убираем пробелы
        product_ids = [pid.strip() for pid in product_ids_str.split(',') if pid.strip()]
        
        # Проверяем, что все значения - числа
        for pid in product_ids:
            if not pid.isdigit():
                return False, []
        
        return True, product_ids
    
    def execute(self) -> Optional[requests.Response]:
        """Выполнение запроса пересчета остатков"""
        product_ids_str = self.param_widgets["productIds"].get().strip()
        remain_type = self.param_widgets["remainType"].get()
        
        # Сбрасываем timestamp и скрываем кнопку
        self.last_response_timestamp = None
        self.view_logs_button.config(state="disabled")
        
        # Проверяем корректность номенклатуры
        is_valid, product_ids = self.validate_product_ids(product_ids_str)
        if not is_valid:
            messagebox.showerror("Ошибка", "Номенклатуры должны содержать только цифры!")
            return None
        
        # Если поле пустое - предупреждение о пересчете всей базы
        if not product_ids:
            confirm = messagebox.askyesno(
                "Подтверждение",
                "Вы не указали номенклатуры. Будет запущен пересчет ВСЕЙ БАЗЫ!\n\nПродолжить?"
            )
            if not confirm:
                return None
        
        try:
            url = self.config["url"]
            
            # Формируем параметры запроса
            params = {"remainType": remain_type}
            
            # Добавляем productIds как multiple параметры
            for pid in product_ids:
                params["productIds"] = pid
            
            # Устанавливаем User-Agent в зависимости от типа запроса
            headers = self.config["headers"].copy()
            if not product_ids:
                headers["User-Agent"] = "OMNIL2_HF"  # Пересчет всей базы
            else:
                headers["User-Agent"] = "HoffApiTool/1.0"  # Пересчет конкретных товаров
            
            # Логируем запрос
            self.log_request(self.config["method"], url, headers, params)
            
            # Выполняем запрос
            response = requests.request(
                method=self.config["method"],
                url=url,
                headers=headers,
                params=params,
                json={},
                timeout=60  # Увеличиваем таймаут для пересчета
            )
            
            # Логируем ответ
            self.log_response(response)
            
            response.raise_for_status()
            
            # Сохраняем timestamp из ответа для создания ссылки на логи
            try:
                response_data = response.json()
                if "result" in response_data and "timestamp" in response_data["result"]:
                    self.last_response_timestamp = response_data["result"]["timestamp"]
                    # Активируем кнопку просмотра логов
                    self.view_logs_button.config(state="normal")
            except (json.JSONDecodeError, KeyError):
                pass
            
            return response

        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка запроса пересчета: {str(e)}"
            messagebox.showerror("Ошибка сети", error_msg)
            return None
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неожиданная ошибка: {str(e)}")
            return None
    
    def open_elk_logs(self):
        """Открытие страницы с логами в ELK"""
        if not self.last_response_timestamp:
            messagebox.showwarning("Предупреждение", "Нет данных о времени выполнения запроса")
            return
        
        try:
            # Парсим timestamp из ответа
            timestamp = datetime.fromisoformat(self.last_response_timestamp.replace('Z', '+00:00'))
            
            # Вычисляем временной диапазон: ±30 секунд от времени запроса
            from_time = timestamp - timedelta(seconds=30)
            to_time = timestamp + timedelta(seconds=30)
            
            # Форматируем время для URL
            from_str = from_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            to_str = to_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # Создаем URL для ELK
            elk_url = (
                f"https://log.kifr-ru.local/s/omni/app/discover#/"
                f"?_g=(filters:!(),refreshInterval:(pause:!t,value:60000),"
                f"time:(from:'{from_str}',to:'{to_str}'))"
                f"&_a=(columns:!(message,MessageTemplate,kubernetes.container.name,trace_id,requestPath,traceId),"
                f"filters:!(),hideChart:!f,index:'97bbcb4e-6ac8-4971-963c-49d9cfbf3655',"
                f"interval:auto,query:(language:kuery,query:%22HoffApiTool%22),"
                f"sort:!(!('@timestamp',desc)))"
            )
            
            # Открываем URL в браузере по умолчанию
            import webbrowser
            webbrowser.open(elk_url)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть логи: {str(e)}")

class GeoApiMethod(ApiMethod):
    """Метод для работы с геоданными без визуализации карты"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.latitude_var = tk.StringVar(value="55.7558")
        self.longitude_var = tk.StringVar(value="37.6173")
        self.address_var = tk.StringVar()
        self.selected_address = tk.StringVar(value="Москва, Россия")
        self.request_source = "ISTORE"  # Значение по умолчанию
        self.request_uid = "1"  # Значение по умолчанию"
    
    def create_ui(self, parent) -> None:
        """Создание UI для гео-метода без карты"""
        for widget in parent.winfo_children():
            widget.destroy()
        
        row = 0
        
        # Информация о параметрах запроса (только для отображения, не для редактирования)
        info_frame = ttk.Frame(parent)
        info_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        ttk.Label(info_frame, text="Параметры запроса (фиксированные):", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        ttk.Label(info_frame, text="RequestSource: ISTORE, RequestUID: 1", font=('Arial', 9)).pack(anchor=tk.W)
        row += 1
        
        # Поиск адреса через Яндекс Геокодер
        ttk.Label(parent, text="Поиск адреса:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        search_frame = ttk.Frame(parent)
        search_frame.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        search_frame.columnconfigure(0, weight=1)
        
        search_entry = ttk.Entry(search_frame, textvariable=self.address_var, width=30)
        search_entry.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        search_entry.bind("<Return>", lambda e: self.search_address())
        
        ttk.Button(search_frame, text="Найти", command=self.search_address).grid(row=0, column=1)
        row += 1
        
        # Выбранный адрес
        ttk.Label(parent, text="Выбранный адрес:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        address_label = ttk.Label(parent, textvariable=self.selected_address, wraplength=400, foreground="blue")
        address_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        row += 1
        
        # Поля для ручного ввода координат
        ttk.Label(parent, text="Широта (latitude):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        lat_entry = ttk.Entry(parent, textvariable=self.latitude_var, width=20)
        lat_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        row += 1
        
        ttk.Label(parent, text="Долгота (longitude):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        lon_entry = ttk.Entry(parent, textvariable=self.longitude_var, width=20)
        lon_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        row += 1
        
        parent.columnconfigure(1, weight=1)
    
    #метод поиска через яндекс апи
    def search_address(self):
        """Поиск адреса через Яндекс Геокодер API"""
        address = self.address_var.get().strip()
        if not address:
            messagebox.showwarning("Ошибка", "Введите адрес для поиска")
            return
        
        try:
            # Используем Яндекс Геокодер API для поиска адреса
            geocoder_url = "https://geocode-maps.yandex.ru/1.x/"
            params = {
                "apikey": "ваш_geocoder_api_ключ",  # Нужен реальный ключ
                "geocode": address,
                "format": "json",
                "lang": "ru_RU"
            }
            
            response = requests.get(geocoder_url, params=params, timeout=10)
            
            # Проверяем статус ответа
            if response.status_code == 403:
                # Если ошибка 403, используем альтернативный метод
                self.fallback_geocoding(address)
                return
                
            response.raise_for_status()
            
            data = response.json()
            
            # Извлекаем координаты из ответа
            features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
            
            if not features:
                messagebox.showinfo("Результат", "Адрес не найден")
                return
            
            # Берем первый результат
            first_result = features[0]["GeoObject"]
            point = first_result["Point"]["pos"]
            lon, lat = point.split(" ")
            
            # Обновляем поля координат
            self.latitude_var.set(lat)
            self.longitude_var.set(lon)
            
            # Обновляем поле адреса
            address_name = first_result["metaDataProperty"]["GeocoderMetaData"]["text"]
            self.selected_address.set(address_name)
            
            messagebox.showinfo("Успех", f"Найден адрес: {address_name}\nКоординаты: {lat}, {lon}")
            
        except requests.exceptions.RequestException as e:
            # При ошибке сети используем альтернативный метод
            self.fallback_geocoding(address)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неожиданная ошибка: {str(e)}")
    
    def fallback_geocoding(self, address):
        """Альтернативный метод геокодирования через Nominatim (OpenStreetMap)"""
        try:
            # Используем Nominatim как резервный вариант
            geocoder_url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": address,
                "format": "json",
                "limit": 1
            }
            
            headers = {
                "User-Agent": "HoffApiTool/1.0 (contact@example.com)"
            }
            
            response = requests.get(geocoder_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                messagebox.showinfo("Результат", "Адрес не найден")
                return
            
            # Берем первый результат
            first_result = data[0]
            lat = first_result["lat"]
            lon = first_result["lon"]
            
            # Обновляем поля координат
            self.latitude_var.set(lat)
            self.longitude_var.set(lon)
            
            # Обновляем поле адреса
            address_name = first_result["display_name"]
            self.selected_address.set(address_name)
            
            messagebox.showinfo("Успешно", f"Найден адрес: {address_name}\nКоординаты: {lat}, {lon}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось найти адрес: {str(e)}")
    
    def get_coordinates(self) -> Optional[Tuple[float, float]]:
        """Получение координат из полей ввода"""
        try:
            latitude = float(self.latitude_var.get().strip())
            longitude = float(self.longitude_var.get().strip())
            
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                raise ValueError("Координаты вне допустимого диапазона")
                
            return latitude, longitude
            
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректные координаты: {str(e)}")
            return None
    
    def execute(self) -> Optional[requests.Response]:
        """Выполнение гео-запроса"""
        coordinates = self.get_coordinates()
        if not coordinates:
            return None
        
        latitude, longitude = coordinates
        
        try:
            # Используем фиксированные значения для RequestSource и RequestUID
            request_body = {
                "RequestSource": self.request_source,
                "RequestUID": self.request_uid,
                "point": {
                    "latitude": latitude,
                    "longitude": longitude
                }
            }
            
            # Логируем запрос
            self.log_request(self.config["method"], self.config["url"], self.config.get("headers", {}), data=request_body)
            
            # Выполняем запрос
            response = requests.request(
                method=self.config["method"],
                url=self.config["url"],
                headers=self.config.get("headers", {}),
                json=request_body,
                timeout=30
            )
            
            # Логируем ответ
            self.log_response(response)
            
            response.raise_for_status()
            
            return response

        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка гео-запроса: {str(e)}"
            messagebox.showerror("Ошибка сети", error_msg)
            return None
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неожиданная ошибка: {str(e)}")
            return None

class ResponseParser:
    """Класс для разбора ответов API"""
    
    @staticmethod
    def parse_response(response_data: Dict[str, Any], content_frame: ttk.Frame) -> None:
        """Разбор ответа API на отдельные фреймы"""
        # Очищаем предыдущие фреймы
        for widget in content_frame.winfo_children():
            widget.destroy()
        
        row = 0
        
        # Общая информация
        if "result" in response_data:
            result_frame = ttk.LabelFrame(
                content_frame, 
                text="Результат выполнения", 
                padding="5"
            )
            result_frame.grid(row=row, column=0, sticky=tk.W+tk.E, pady=5, padx=5)
            row += 1
            
            for key, value in response_data["result"].items():
                ttk.Label(result_frame, text=f"{key}:", font=('Arial', 9, 'bold')).grid(
                    sticky=tk.W, padx=5, pady=2)
                ttk.Label(result_frame, text=str(value)).grid(
                    sticky=tk.W, padx=15, pady=2)
        
        # Данные
        if "data" in response_data:
            ResponseParser._parse_data(response_data["data"], content_frame, row)
    
    @staticmethod
    def _parse_data(data: Dict[str, Any], parent, start_row: int) -> None:
        """Разбор данных ответа"""
        data_frame = ttk.LabelFrame(
            parent, 
            text="Данные", 
            padding="5"
            )
        data_frame.grid(row=start_row, column=0, sticky=tk.W+tk.E, pady=5, padx=5)
        row = 0
        
        # Базовые поля данных
        for key, value in data.items():
            if key != "products":  # Обработаем продукты отдельно
                ttk.Label(data_frame, text=f"{key}:", font=('Arial', 9, 'bold')).grid(
                    row=row, column=0, sticky=tk.W, padx=5, pady=2)
                ttk.Label(data_frame, text=str(value)).grid(
                    row=row, column=1, sticky=tk.W, padx=15, pady=2)
                row += 1
        
        # Обработка продуктов
        if "products" in data and isinstance(data["products"], list):
            ResponseParser._parse_products(data["products"], data_frame, row)

    @staticmethod
    def _parse_products(products: List[Dict[str, Any]], parent, start_row: int) -> None:
        """Разбор информации о продуктах"""
        products_frame = ttk.LabelFrame(
            parent, 
            text="Товары", 
            padding="5"
        )
        products_frame.grid(row=start_row, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5, padx=5)
        
        for i, product in enumerate(products):
            product_frame = ttk.LabelFrame(
                products_frame, 
                text=f"Товар {i+1}", 
                padding="5"
            )
            product_frame.grid(row=i, column=0, sticky=tk.W+tk.E, pady=2, padx=5)
            
            # Основная информация о товаре
            if "productId" in product:
                ttk.Label(product_frame, text="ID товара:", font=('Arial', 9, 'bold')).grid(
                    row=0, column=0, sticky=tk.W, padx=5, pady=2)
                ttk.Label(product_frame, text=product["productId"]).grid(
                    row=0, column=1, sticky=tk.W, padx=15, pady=2)
            
            # Параметры товара
            if "productParameter" in product:
                ResponseParser._parse_product_parameters(product["productParameter"], product_frame, 1)
            
            # Остатки
            if "remains" in product and isinstance(product["remains"], list):
                ResponseParser._parse_remains(product["remains"], product_frame, 2)

    @staticmethod
    def _parse_product_parameters(parameters: Dict[str, Any], parent, row: int) -> None:
        """Разбор параметров товара"""
        param_frame = ttk.LabelFrame(
            parent, 
            text="Параметры товара", 
            padding="5"
        )
        param_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W+tk.E, pady=2, padx=5)
        
        for i, (key, value) in enumerate(parameters.items()):
            ttk.Label(param_frame, text=f"{key}:").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=1)
            ttk.Label(param_frame, text=str(value)).grid(
                row=i, column=1, sticky=tk.W, padx=15, pady=1)

    @staticmethod
    def _parse_remains(remains: List[Dict[str, Any]], parent, row: int) -> None:
        """Разбор информации об остатках"""
        remains_frame = ttk.LabelFrame(
            parent, 
            text="Остатки", 
            padding="5"
        )
        remains_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W+tk.E, pady=2, padx=5)
        
        for j, remain in enumerate(remains):
            remain_item_frame = ttk.Frame(remains_frame, padding="3")
            remain_item_frame.grid(row=j, column=0, sticky=tk.W+tk.E, pady=2)
            
            ttk.Label(remain_item_frame, text=f"Остаток {j+1}", font=('Arial', 8, 'bold')).grid(
                row=0, column=0, sticky=tk.W, padx=5)
            
            for k, (key, value) in enumerate(remain.items(), start=1):
                ttk.Label(remain_item_frame, text=f"{key}:").grid(
                    row=k, column=0, sticky=tk.W, padx=5)
                ttk.Label(remain_item_frame, text=str(value)).grid(
                    row=k, column=1, sticky=tk.W, padx=15)

class ContextMenu:
    """Класс для управления контекстным меню"""
    
    def __init__(self, parent):
        self.parent = parent
        self.menu = tk.Menu(parent, tearoff=0)
        self.menu.add_command(label="Копировать", command=self.copy_to_clipboard)
        self.menu.add_command(label="Вставить", command=self.paste_from_clipboard)
        self.menu.add_command(label="Очистить", command=self.clear_field)
        self.current_widget = None
    
    def show(self, event):
        """Отображение контекстного меню"""
        self.current_widget = event.widget
        self.menu.tk_popup(event.x_root, event.y_root)
    
    def copy_to_clipboard(self):
        """Копирование в буфер обмена"""
        if self.current_widget:
            try:
                selected_text = self.current_widget.selection_get()
                self.parent.clipboard_clear()
                self.parent.clipboard_append(selected_text)
            except tk.TclError:
                pass
    def paste_from_clipboard(self):
        """Вставка из буфер обмена"""
        if self.current_widget and isinstance(self.current_widget, tk.Entry):
            try:
                clipboard_content = self.parent.clipboard_get()
                self.current_widget.delete(0, tk.END)
                self.current_widget.insert(0, clipboard_content)
            except tk.TclError:
                messagebox.showwarning("Ошибка", "Буфер обмена пуст")
    
    def clear_field(self):
        """Очистка поля"""
        if self.current_widget and isinstance(self.current_widget, tk.Entry):
            self.current_widget.delete(0, tk.END)

class ConsoleHandler(logging.Handler):
    """Обработчик логов для вывода в консольное окно"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')

class HoffApiTool:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.window = tk.Toplevel(parent_window)
        self.window.title("Hoff API Tool")
        self.window.geometry("1200x800")
        
        self.api_methods = self._initialize_api_methods()
        self.current_method = None
        self.context_menu = ContextMenu(self.window)
        
        # Создаем виджет для консоли
        self.console_text = None
        self.create_widgets()
        
        # Добавляем обработчик для вывода логов в консольное окно
        console_handler = ConsoleHandler(self.console_text)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    def _initialize_api_methods(self) -> Dict[str, ApiMethod]:
        """Инициализация методов API"""
        methods_config = {
            "Запрос остатков ИМ": {
                "url": "https://apps.prod-omni.hoff.ru/inventory-atomic/v1/order/remain",
                "method": "POST",
                "headers": {
                    'accept': '*/*',
                    'Content-Type': 'application/json'
                },
                "params": {
                    "Hoff-Business-Unit-Id": {"type": "entry", "required": True},
                    "productId": {"type": "entry", "required": True},
                    "isMinPriority": {"type": "check", "default": "true"}
                },
                "body": {
                    "products": [{"productId": ""}],
                    "isMinPriority": True
                }
            },
            "Запрос корзины": {
                "url": "https://apps.prod-omni.hoff.ru/web-ecomm-bff/cart/v1/items",
                "method": "GET",
                "headers": {
                    'Content-Type': 'application/json'
                },
                "params": {
                    "Hoff-DeliveryZoneId": {"type": "entry", "required": True},
                    "Hoff-Request-Source": {"type": "combobox", "values": ["ISTORE", "MOBILE"], "default": "ISTORE"},
                    "Hoff-businessunitid": {"type": "entry", "required": True},
                    "Authorization": {"type": "entry", "width": 60, "required": True, "sensitive": True}
                }
            },
            "Запрос геоданных": {
                "url": "https://api.hoff.ru/geoGetIStoreBUByPoint/zone",
                "method": "POST",
                "headers": {
                    'Content-Type': 'application/json'
                },
                "params": {
                    "RequestSource": {"type": "combobox", "values": ["ISTORE", "MOBILE"], "default": "ISTORE", "required": True},
                    "RequestUID": {"type": "entry", "required": True, "default": "1"}
                }
            },
            "Пересчет остатков": {
                "url": "https://apps.prod-omni.hoff.ru/inventory-atomic/v1/calculation/remain",
                "method": "POST",
                "headers": {
                    'accept': '*/*'
                }
            }
        }
        
        methods = {}
        for name, config in methods_config.items():
            match name:
                case "Запрос геоданных":
                    methods[name] = GeoApiMethod(name, config)
                case "Пересчет остатков":
                    methods[name] = CalculationApiMethod(name, config)
                case _:
                    methods[name] = StandardApiMethod(name, config)
        
        return methods

    def create_widgets(self):
        """Создание GUI компонентов"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Выбор метода API
        method_frame = ttk.LabelFrame(main_frame, text="Выбор метода API", padding="10")
        method_frame.pack(fill=tk.X, pady=5)
        
        self.method_var = tk.StringVar()
        self.method_combobox = ttk.Combobox(
            method_frame,
            textvariable=self.method_var,
            values=list(self.api_methods.keys()),
            state="readonly",
            width=40
        )
        self.method_combobox.pack(fill=tk.X, padx=5, pady=5)
        self.method_combobox.bind("<<ComboboxSelected>>", self.on_method_selected)

        # Область параметров
        self.params_frame = ttk.LabelFrame(main_frame, text="Параметры запроса", padding="10")
        self.params_frame.pack(fill=tk.X, pady=5)

        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Выполнить запрос", command=self.execute_request).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить консоль", command=self.clear_console).pack(side=tk.LEFT, padx=5)

        # Область результатов
        result_frame = ttk.LabelFrame(main_frame, text="Результаты", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем Notebook для вкладок с результатами
        self.result_notebook = ttk.Notebook(result_frame)
        self.result_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка с полным ответом
        self.full_response_tab = ttk.Frame(self.result_notebook)
        self.result_notebook.add(self.full_response_tab, text="Полный ответ")
        
        self.full_response_text = scrolledtext.ScrolledText(
            self.full_response_tab, 
            wrap=tk.WORD, 
            font=('Consolas', 10)
        )
        self.full_response_text.pack(fill=tk.BOTH, expand=True)
        
        # Вкладка с разобранным ответом
        self.parsed_response_tab = ttk.Frame(self.result_notebook)
        self.result_notebook.add(self.parsed_response_tab, text="Разобранный ответ")
        
        # Canvas и Scrollbar для разобранного ответа
        self.parsed_canvas = tk.Canvas(self.parsed_response_tab)
        self.parsed_scrollbar = ttk.Scrollbar(
            self.parsed_response_tab, 
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
        
        # Вкладка с консолью
        self.console_tab = ttk.Frame(self.result_notebook)
        self.result_notebook.add(self.console_tab, text="Консоль")
        
        self.console_text = scrolledtext.ScrolledText(
            self.console_tab,
            wrap=tk.WORD,
            font=('Consolas', 9),
            state='disabled'
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)

        # Статус бар
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(5, 0))

    def on_method_selected(self, event=None):
        """Обработчик выбора метода API"""
        method_name = self.method_var.get()
        if method_name in self.api_methods:
            self.current_method = self.api_methods[method_name]
            self.current_method.create_ui(self.params_frame)
            
            # Добавляем контекстное меню ко всем полям ввода
            for widget in self.params_frame.winfo_children():
                if isinstance(widget, tk.Entry):
                    widget.bind("<Button-3>", self.context_menu.show)
                    widget.bind("<Control-v>", lambda e: self.context_menu.paste_from_clipboard())

    def execute_request(self):
        """Выполнение API-запроса"""
        if not self.current_method:
            messagebox.showwarning("Ошибка", "Выберите метод API")
            return

        response = self.current_method.execute()
        if not response:
            self.status_var.set("Ошибка выполнения запроса")
            return

        # Очистка предыдущих результатов
        self.clear_results()
        
        # Вывод полного ответа
        self.full_response_text.insert(tk.END, f"Статус: {response.status_code}\n")
        
        try:
            response_data = response.json()
            formatted_response = json.dumps(response_data, indent=2, ensure_ascii=False)
            self.full_response_text.insert(tk.END, f"Ответ сервера:\n{formatted_response}")
            
            # Разбор ответа на отдельные фреймы
            ResponseParser.parse_response(response_data, self.parsed_content_frame)
            
            self.status_var.set(f"Запрос выполнен успешно ({response.status_code})")

        except json.JSONDecodeError:
            self.full_response_text.insert(tk.END, f"Ответ сервера (не JSON):\n{response.text}")
            self.status_var.set(f"Получен текстовый ответ ({response.status_code})")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка обработки ответа: {str(e)}")
            self.status_var.set("Ошибка обработки ответа")

    def clear_results(self):
        """Очистка результатов"""
        self.full_response_text.delete(1.0, tk.END)
        for widget in self.parsed_content_frame.winfo_children():
            widget.destroy()
        self.status_var.set("")
        
    def clear_console(self):
        """Очистка консоли"""
        self.console_text.configure(state='normal')
        self.console_text.delete(1.0, tk.END)
        self.console_text.configure(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = HoffApiTool(root)
    root.mainloop()