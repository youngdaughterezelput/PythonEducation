import os
import sys
import tkinter as tk
from tkinter import messagebox

class IconManager:
    def __init__(self, root=None):
        self.root = root
        self.icon_path = self._find_icon()
    
    def _find_icon(self):
        """Поиск иконки в возможных расположениях"""
        possible_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.ico"),
            os.path.join(sys._MEIPASS, "icon.ico") if hasattr(sys, '_MEIPASS') else None,
            "icon.ico"
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                return path
        
        return None
    
    def set_icon(self, window):
        """Установка иконки для конкретного окна"""
        if not self.icon_path:
            print("Иконка не найдена")
            return False
        
        try:
            window.iconbitmap(self.icon_path)
            return True
        except Exception as e:
            print(f"Ошибка установки иконки: {e}")
            return False
    
    def set_icon_for_all(self):
        """Установка иконки для всех будущих окон через root"""
        if self.icon_path and self.root:
            try:
                self.root.option_add('*iconBitmap', self.icon_path)
                return True
            except Exception as e:
                print(f"Ошибка установки глобальной иконки: {e}")
                return False
        return False