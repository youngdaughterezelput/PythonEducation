import os
import sys
import tkinter as tk
from main_controller import MainController
from icon_manager import IconManager
from updater import Updater

class MainApplication:
    def __init__(self):
        self.root = tk.Tk()
        self.current_version = "1.0.0"  # Укажите текущую версию вашего приложения
        
        # 1. Сначала инициализируем базовые атрибуты
        self.icon_manager = IconManager(self.root)
        
        # 2. Затем создаем updater
        self.updater = Updater(self.root, self.current_version)  # Используем current_version
        
        # 3. Потом создаем контроллер и передаем ему updater
        self.controller = MainController(root=self.root, updater=self.updater)
        
        # 4. Настраиваем иконку
        self.icon_manager.set_icon(self.root)
        
        # 5. Запускаем проверку обновлений
        self.updater.check_for_updates(silent=True)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MainApplication()
    app.run()