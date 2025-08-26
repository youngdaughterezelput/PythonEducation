import requests
import base64
import os
import tkinter as tk
from tkinter import ttk, ttk, messagebox
from .security_manager import SecurityManager
from datetime import datetime, timedelta, timezone

class SoapConnector:
    def __init__(self):
        self.auth = None
        self.url = "http://pos-d-001.kifr-ru.local:8083/POSProcessing.asmx"
        self.headers = {
            'Accept': 'text/xml',
            'Content-Type': 'text/xml',
            'SOAPAction': '"http://loyalty.manzanagroup.ru/loyalty.xsd/ProcessRequest"'
        }
    
    def check_auth(self):
        self.auth = SecurityManager.get_password('SOAP_AUTH', 'env') or os.getenv('SOAP_AUTH')
        return self.auth is not None
    
    def show_auth_dialog(self, parent_window, callback):
        dialog = tk.Toplevel(parent_window)
        dialog.title("Авторизация SOAP")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Логин:").grid(row=0, column=0, sticky=tk.W, pady=5)
        login_entry = ttk.Entry(main_frame, width=30)
        login_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(main_frame, text="Пароль:").grid(row=1, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(main_frame, width=30, show="*")
        password_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        save_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            main_frame,
            text="Сохранить настройки",
            variable=save_var
        ).grid(row=2, column=0, columnspan=2, pady=10, sticky=tk.W)
        
        def on_submit():
            login = login_entry.get().strip()
            password = password_entry.get().strip()
            
            if not login or not password:
                messagebox.showerror("Ошибка", "Заполните все поля")
                return
            
            auth_str = f"{login}:{password}"
            self.auth = base64.b64encode(auth_str.encode()).decode()
            
            if save_var.get():
                SecurityManager.store_password('SOAP_AUTH', self.auth, 'env')
            
            os.environ['SOAP_AUTH'] = self.auth
            dialog.destroy()
            callback()
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Подтвердить", command=on_submit).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def send_request(self, soap_data):
        if not self.auth:
            return {'status': 'Ошибка', 'code': 'N/A', 'response': 'Нет данных авторизации'}
        
        headers = self.headers.copy()
        headers['Authorization'] = f'Basic {self.auth}'
        
        try:
            response = requests.post(self.url, headers=headers, data=soap_data)
            return {
                'status': 'Успех' if response.status_code == 200 else 'Ошибка',
                'code': response.status_code,
                'response': response.text
            }
        except Exception as e:
            return {
                'status': 'Ошибка',
                'code': 'N/A',
                'response': str(e)
            }
    
    @staticmethod
    def format_datetime(dt_obj):
        """Форматирует объект datetime в строку для SOAP"""
        try:
            # Если есть часовой пояс - конвертируем в UTC
            if dt_obj.tzinfo is not None:
                dt_obj = dt_obj.astimezone(timezone.utc)
            else:
                # Считаем что время в UTC
                dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                
            return dt_obj.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        except Exception:
            # Fallback: текущее время в UTC
            utc_time = datetime.now(timezone.utc)
            return utc_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'