import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from logger_module import Logger
from security_manager import SecurityManager

class SettingsWindow:
    def __init__(self, parent):
        self.parent = parent
        self.settings_file = "app_settings.json"
        self.logger = Logger()
        self.settings = self.load_settings()
        
        self.window = tk.Toplevel(parent)
        self.window.title("Настройки приложения")
        self.window.geometry("500x400")
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Создаем Notebook для вкладок
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем вкладки
        self.create_general_tab()
        self.create_connection_tab()
        self.create_appearance_tab()
        self.create_security_tab()
        self.create_buttons()

        self.logger.log('INFO', 'Окно настроек инициализировано')

    def create_security_tab(self):
        """Вкладка безопасности"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Безопасность")
        
        # Кнопка очистки паролей
        ttk.Button(
            tab,
            text="Очистить все сохраненные пароли",
            command=self.clear_all_passwords,
            style="Danger.TButton"
        ).pack(pady=20, padx=10, fill=tk.X)
        
        ttk.Label(
            tab,
            text="Это действие удалит все сохраненные пароли во всех формах приложения",
            foreground="red"
        ).pack(pady=5)
        
        # Стиль для опасной кнопки
        style = ttk.Style()
        style.configure("Danger.TButton", foreground="white", background="#d9534f")

    def clear_all_passwords(self):
        """Очистка всех сохраненных паролей"""
        if messagebox.askyesno(
            "Подтверждение",
            "Вы уверены, что хотите удалить ВСЕ сохраненные пароли?\n"
            "Это действие затронет все формы приложения и необратимо!"
        ):
            try:
                SecurityManager.clear_all_passwords()
                self.logger.log('INFO', 'Все сохраненные пароли были очищены')
                messagebox.showinfo("Успех", "Все сохраненные пароли успешно удалены!")
            except Exception as e:
                self.logger.log('ERROR', f'Ошибка очистки паролей: {str(e)}')
                messagebox.showerror("Ошибка", f"Не удалось очистить пароли: {str(e)}")
    
    def create_general_tab(self):
        """Создаем вкладку основных настроек"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Основные")
        
        # Автозагрузка
        ttk.Label(tab, text="Автозагрузка:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.autoload_var = tk.BooleanVar(value=self.settings.get("autoload", False))
        ttk.Checkbutton(tab, variable=self.autoload_var, text="Загружать последний файл при запуске").grid(
            row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Язык интерфейса
        ttk.Label(tab, text="Язык интерфейса:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.language_var = tk.StringVar(value=self.settings.get("language", "ru"))
        lang_combobox = ttk.Combobox(
            tab, 
            textvariable=self.language_var,
            values=["ru", "en", "de"],
            state="readonly",
            width=10
        )
        lang_combobox.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Логирование
        ttk.Label(tab, text="Уровень логирования:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.log_level_var = tk.StringVar(value=self.settings.get("log_level", "INFO"))
        log_combobox = ttk.Combobox(
            tab, 
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            state="readonly",
            width=15
        )
        log_combobox.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Максимальное количество файлов в истории
        ttk.Label(tab, text="Файлов в истории:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.history_size_var = tk.IntVar(value=self.settings.get("history_size", 10))
        ttk.Spinbox(
            tab,
            from_=1,
            to=50,
            textvariable=self.history_size_var,
            width=5
        ).grid(row=3, column=1, sticky="w", padx=5, pady=5)
    
    def create_connection_tab(self):
        """Создаем вкладку настроек подключения"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Подключения")
        
        # URL API сервера
        ttk.Label(tab, text="API URL:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.api_url_var = tk.StringVar(value=self.settings.get("api_url", "http://api.example.com"))
        ttk.Entry(tab, textvariable=self.api_url_var, width=40).grid(
            row=0, column=1, sticky="we", padx=5, pady=5)
        
        # Таймаут подключения
        ttk.Label(tab, text="Таймаут (сек):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.timeout_var = tk.IntVar(value=self.settings.get("timeout", 30))
        ttk.Spinbox(
            tab,
            from_=1,
            to=120,
            textvariable=self.timeout_var,
            width=5
        ).grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Прокси
        ttk.Label(tab, text="Использовать прокси:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.use_proxy_var = tk.BooleanVar(value=self.settings.get("use_proxy", False))
        ttk.Checkbutton(tab, variable=self.use_proxy_var).grid(
            row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Настройки прокси
        self.proxy_frame = ttk.LabelFrame(tab, text="Настройки прокси")
        self.proxy_frame.grid(row=3, column=0, columnspan=2, sticky="we", padx=5, pady=5)
        
        ttk.Label(self.proxy_frame, text="Адрес:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.proxy_host_var = tk.StringVar(value=self.settings.get("proxy_host", ""))
        ttk.Entry(self.proxy_frame, textvariable=self.proxy_host_var, width=30).grid(
            row=0, column=1, sticky="we", padx=5, pady=2)
        
        ttk.Label(self.proxy_frame, text="Порт:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.proxy_port_var = tk.StringVar(value=self.settings.get("proxy_port", ""))
        ttk.Entry(self.proxy_frame, textvariable=self.proxy_port_var, width=10).grid(
            row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(self.proxy_frame, text="Логин:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.proxy_user_var = tk.StringVar(value=self.settings.get("proxy_user", ""))
        ttk.Entry(self.proxy_frame, textvariable=self.proxy_user_var, width=30).grid(
            row=2, column=1, sticky="we", padx=5, pady=2)
        
        ttk.Label(self.proxy_frame, text="Пароль:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.proxy_pass_var = tk.StringVar(value=self.settings.get("proxy_pass", ""))
        ttk.Entry(self.proxy_frame, textvariable=self.proxy_pass_var, width=30, show="*").grid(
            row=3, column=1, sticky="we", padx=5, pady=2)
        
        # Обновляем видимость настроек прокси
        self.update_proxy_settings_visibility()
        self.use_proxy_var.trace("w", lambda *args: self.update_proxy_settings_visibility())

    def update_proxy_settings_visibility(self):
        """Обновляем видимость настроек прокси"""
        if self.use_proxy_var.get():
            self.proxy_frame.grid()
        else:
            self.proxy_frame.grid_remove()
    
    def create_appearance_tab(self):
        """Создаем вкладку настроек внешнего вида"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Внешний вид")
        
        # Тема приложения
        ttk.Label(tab, text="Тема:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "light"))
        theme_combobox = ttk.Combobox(
            tab, 
            textvariable=self.theme_var,
            values=["light", "dark", "system"],
            state="readonly",
            width=15
        )
        theme_combobox.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Размер шрифта
        ttk.Label(tab, text="Размер шрифта:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.font_size_var = tk.IntVar(value=self.settings.get("font_size", 10))
        ttk.Spinbox(
            tab,
            from_=8,
            to=20,
            textvariable=self.font_size_var,
            width=5
        ).grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Показывать иконки
        ttk.Label(tab, text="Иконки:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.show_icons_var = tk.BooleanVar(value=self.settings.get("show_icons", True))
        ttk.Checkbutton(tab, variable=self.show_icons_var, text="Показывать иконки в меню").grid(
            row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Прозрачность окна
        ttk.Label(tab, text="Прозрачность:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.opacity_var = tk.DoubleVar(value=self.settings.get("opacity", 1.0))
        opacity_scale = ttk.Scale(
            tab,
            from_=0.1,
            to=1.0,
            variable=self.opacity_var,
            length=200
        )
        opacity_scale.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        
        # Значение прозрачности
        opacity_value = ttk.Label(tab, text=f"{self.opacity_var.get():.1f}")
        opacity_value.grid(row=3, column=2, sticky="w", padx=5, pady=5)
        
        # Обновление значения прозрачности в реальном времени
        self.opacity_var.trace("w", lambda *args: opacity_value.config(
            text=f"{self.opacity_var.get():.1f}"))
    
    def create_buttons(self):
        """Создаем кнопки сохранения/отмены"""
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            button_frame,
            text="Сохранить",
            command=self.save_settings,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Отмена",
            command=self.on_close
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame,
            text="По умолчанию",
            command=self.reset_defaults
        ).pack(side=tk.LEFT, padx=5)
    
    def load_settings(self):
        """Загрузка настроек из файла"""
        default_settings = self.get_default_settings()
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                    # Применяем прозрачность при загрузке
                    self.parent.attributes('-alpha', loaded_settings.get("opacity", 1.0))
                    return loaded_settings
            return default_settings
        except Exception as e:
            self.logger.log('ERROR', f'Ошибка загрузки настроек: {str(e)}')
            return default_settings

    def get_default_settings(self):
        """Возвращает настройки по умолчанию"""
        return {
            "autoload": False,
            "language": "ru",
            "log_level": "INFO",
            "history_size": 10,
            "api_url": "http://api.example.com",
            "timeout": 30,
            "use_proxy": False,
            "proxy_host": "",
            "proxy_port": "",
            "proxy_user": "",
            "proxy_pass": "",
            "theme": "light",
            "font_size": 10,
            "show_icons": True,
            "opacity": 1.0
        }
    
    def save_settings(self):
        """Сохранение настроек в файл"""
        new_settings = {
            "autoload": self.autoload_var.get(),
            "language": self.language_var.get(),
            "log_level": self.log_level_var.get(),
            "history_size": self.history_size_var.get(),
            "api_url": self.api_url_var.get(),
            "timeout": self.timeout_var.get(),
            "use_proxy": self.use_proxy_var.get(),
            "proxy_host": self.proxy_host_var.get(),
            "proxy_port": self.proxy_port_var.get(),
            "proxy_user": self.proxy_user_var.get(),
            "proxy_pass": self.proxy_pass_var.get(),
            "theme": self.theme_var.get(),
            "font_size": self.font_size_var.get(),
            "show_icons": self.show_icons_var.get(),
            "opacity": self.opacity_var.get()
        }
        
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(new_settings, f, ensure_ascii=False, indent=4)
            
            # Применяем прозрачность к главному окну
            self.parent.attributes('-alpha', new_settings["opacity"])
            
            self.logger.log('INFO', 'Настройки сохранены')
            messagebox.showinfo("Успех", "Настройки успешно сохранены!")
        except Exception as e:
            self.logger.log('ERROR', f'Ошибка сохранения настроек: {str(e)}')
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {str(e)}")

    def reset_defaults(self):
        """Сброс настроек к значениям по умолчанию"""
        if messagebox.askyesno("Подтверждение", "Сбросить все настройки к значениям по умолчанию?"):
            default_settings = self.get_default_settings()
            
            # Обновляем значения в интерфейсе
            self.autoload_var.set(default_settings["autoload"])
            self.language_var.set(default_settings["language"])
            self.log_level_var.set(default_settings["log_level"])
            self.history_size_var.set(default_settings["history_size"])
            self.api_url_var.set(default_settings["api_url"])
            self.timeout_var.set(default_settings["timeout"])
            self.use_proxy_var.set(default_settings["use_proxy"])
            self.proxy_host_var.set(default_settings["proxy_host"])
            self.proxy_port_var.set(default_settings["proxy_port"])
            self.proxy_user_var.set(default_settings["proxy_user"])
            self.proxy_pass_var.set(default_settings["proxy_pass"])
            self.theme_var.set(default_settings["theme"])
            self.font_size_var.set(default_settings["font_size"])
            self.show_icons_var.set(default_settings["show_icons"])
            self.opacity_var.set(default_settings["opacity"])
            
            # Применяем прозрачность
            self.parent.attributes('-alpha', default_settings["opacity"])
            
            self.logger.log('INFO', 'Сброс настроек к умолчаниям')

    def on_close(self):
        """Обработчик закрытия окна"""
        self.logger.log('INFO', 'Закрытие окна настроек')
        self.window.destroy()

# Пример использования
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    # Создаем стиль для акцентной кнопки
    style = ttk.Style()
    style.configure("Accent.TButton", foreground="white", background="#0078d7")
    
    # Открываем окно настроек
    settings = SettingsWindow(root)
    
    root.mainloop()