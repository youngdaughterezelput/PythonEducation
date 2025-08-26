import tkinter as tk
from tkinter import ttk
from .analyz_jwt import JWTAnalyzerApp 
from .checkStockInv import InvCheck
from .checkBB import BalanceChecker
from .rejectedApp import PaymentRejectedApp
from .loyalty_app import LoyaltyOperationsApp
from .coupon_app import CouponOperationsApp
from .prom_link import PrometheusAlertsApp
from .reports_launcher import ReportsLauncher
from icon_manager import IconManager

class ToolsHF(tk.Tk):
    def __init__(self):
        super().__init__()
        self.icon_manager = IconManager()
        self.title("Инструменты Hoff")
        self.geometry("900x600")
        # Инициализация менеджера иконок с передачей root
        self.icon_manager = IconManager()
        # Установка иконки
        self.icon_manager.set_icon(self)
        self.modules = {}
        self.current_module = None
        
        self.create_widgets()
        self.load_modules()
    
    def create_widgets(self):
        # Панель выбора модулей
        control_frame = ttk.Frame(self, padding=10)
        control_frame.pack(fill=tk.X)
        
        ttk.Label(control_frame, text="Выберите инструмент:").pack(side=tk.LEFT)
        
        self.module_selector = ttk.Combobox(control_frame, state='readonly', width=40)
        self.module_selector.pack(side=tk.LEFT, padx=10)
        self.module_selector.bind("<<ComboboxSelected>>", self.change_module)
        
        # Контейнер для модулей
        self.module_container = ttk.Frame(self)
        self.module_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def load_modules(self):
        """Регистрация доступных модулей"""
        self.modules = {
            "Анализатор JWT": JWTAnalyzerApp,
            "Проверить остаток по типу из БД": InvCheck,
            "Проверить ББ карт (Запрос к Manzana)": BalanceChecker,
            "Операции с анхолдом ББ": LoyaltyOperationsApp,
            "Операции с анхолдом купонов": CouponOperationsApp,
            "Проверка отмененных транзакций": PaymentRejectedApp,
            "Просмотр текущих алертов списком": PrometheusAlertsApp,
            "Отчеты": ReportsLauncher
        }
        self.module_selector['values'] = list(self.modules.keys())
    
    def change_module(self, event=None):
        """Обработчик смены модуля"""
        # Закрываем текущий модуль
        if self.current_module:
            self.current_module.window.destroy()
            self.current_module = None
        
        # Получаем выбранный модуль
        module_name = self.module_selector.get()
        
        if module_name:
            module_class = self.modules.get(module_name)
            
            if module_class:
                # Обновляем заголовок окна
                self.title(f"Инструменты Hoff - {module_name}")
                
                # Создаем экземпляр модуля в контейнере
                self.current_module = module_class(self.module_container)
                self.current_module.window.pack(fill=tk.BOTH, expand=True)
        else:
            # Возвращаем базовый заголовок если ничего не выбрано
            self.title("Инструменты Hoff")
