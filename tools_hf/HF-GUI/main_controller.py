import os
import sys
from auth_window import AuthWindow
from main_menu import MainMenu
from sendApiMethods import HoffApiTool
from settings import SettingsWindow
import tkinter as tk
from tkinter import messagebox
from hfpoint.gui.main_window import FDWGUI
from sendMesKafka import KafkaProducerApp
from tools_hf.tools import ToolsHF
from icon_manager import IconManager
from updater import Updater

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

class MainController:
    def __init__(self, root, updater=None):
        self.root = root
        self.updater = updater  #  как атрибут
        self.icon_manager = IconManager(root)
        self._initialize_ui()
        self._setup_auth()
    
    def _initialize_ui(self):
        """Инициализация интерфейса"""
        self.root.title("HF GUI")
        self.root.withdraw()
        self.is_admin = False

    def _setup_auth(self):
        """Настройка авторизации"""
        self.icon_manager.set_icon(self.auth_window.window)
        self.auth_window = AuthWindow(self.root, self.on_auth_success)
        
    
    def _set_child_icon(self, window):
        """Установка иконки для дочернего окна"""
        self.icon_manager.set_icon(window)
    
    def _setup_auth(self):
        """Настройка авторизации"""
        self.auth_window = AuthWindow(self.root, self.on_auth_success)

    def _set_child_icon(self, window):
        """Установка иконки для дочернего окна"""
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
            window.iconbitmap(icon_path)
        except Exception as e:
            print(f"Ошибка установки иконки: {e}")
    
    def on_auth_success(self, is_admin=False):
        """Действия после авторизации"""
        self.is_admin = is_admin
        self.root.deiconify()
        self._center_window(350, 200)
        self.menu = MainMenu(self.root, self)
        
        #if is_admin:
        #    self.menu.add_admin_menu(self._show_admin_tools)
    
    def _center_window(self, width, height):
        """Центрирование окна"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 5) - (width // -10)
        y = (screen_height // -5) - (height // 10)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def sendKafka   (self):
        KafkaProducerApp()

    def open_tools(self):
        ToolsHF()
    
    def open_sendApi(self):
        HoffApiTool(self.root)

    def openSetting(self):
        SettingsWindow(self.root)
    
    def exit_click(self):
        self.root.quit()

    def openOmniPoint(self):
        FDWGUI()
    
    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        self._set_child_icon(about_window)
        about_text = "HF GUI 2025"
        tk.Label(about_window, text=about_text).pack(padx=20, pady=20)

    def check_updates(self):  # Добавляем self как первый параметр
        """Обработчик ручной проверки обновлений"""
        if hasattr(self, 'updater'):
            self.updater.manual_check_update()
        else:
            messagebox.showerror("Ошибка", "Модуль обновлений не инициализирован")