import tkinter as tk
from tkinter import ttk, messagebox
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
import sys
import pystray
from PIL import Image, ImageDraw
import threading
import os

class AuthWindow:
    def __init__(self, master, on_success_callback):
        self.master = master
        self.on_success = on_success_callback
        self.window = tk.Toplevel(master)
        self.tray_icon = None
        
        # Инициализация переменных
        self.auth_type = tk.StringVar(value="domain")
        self.auth_frame = None
        
        self._setup_window()
        self._create_widgets()
        self._handle_auth_switcher()
        self._create_tray_icon()

    def _setup_window(self):
        """Настройка основного окна"""
        self.window.title("Авторизация")
        self.window.resizable(False, False)
        
        # Установка иконки
        try:
            if os.path.exists('icon.ico'):
                self.window.iconbitmap(default='icon.ico')
        except Exception:
            pass
        
        # Настройка стилей
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#f5f5f5')
        style.configure('TLabel', background='#f5f5f5', font=('Segoe UI', 9))
        style.configure('TButton', font=('Segoe UI', 9))
        style.configure('TEntry', font=('Segoe UI', 9), padding=5)
        style.configure('TRadiobutton', background='#f5f5f5', font=('Segoe UI', 9))
        
        # Специальный стиль для кнопки входа
        style.configure('Primary.TButton', 
                       foreground='white', 
                       background='#4285f4',
                       font=('Segoe UI', 10, 'bold'),
                       padding=6)
        style.map('Primary.TButton',
                 background=[('active', '#3367d6'), ('pressed', '#2a56c0')])
        
        # Размер окна
        height = 220 if self._check_advanced_mode() else 180
        self.window.geometry(f"320x{height}")
        self.window.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self._center_window()

    def _create_tray_icon(self):
        """Создание иконки в системном трее"""
        def create_image():
            image = Image.new('RGB', (64, 64), color='#4285f4')
            draw = ImageDraw.Draw(image)
            draw.text((10, 10), "Auth", fill='white')
            return image
        
        menu = (
            pystray.MenuItem('Открыть', self.restore_from_tray),
            pystray.MenuItem('Выход', self.quit_application)
        )
        
        self.tray_icon = pystray.Icon("auth_app", create_image(), "Авторизация", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _create_widgets(self):
        """Создание всех элементов интерфейса"""
        main_frame = ttk.Frame(self.window, padding=(15, 15))
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Заголовок
        ttk.Label(main_frame, 
                 text="🔐 Авторизация", 
                 font=('Segoe UI', 12, 'bold'),
                 anchor=tk.CENTER).pack(pady=(0, 15))
        
        # Поля ввода
        self._create_input_fields(main_frame)
        
        # Переключатели типа авторизации
        self._create_auth_switcher(main_frame)
        
        # Кнопки
        self._create_action_buttons(main_frame)

    def _create_input_fields(self, parent):
        """Создание полей для ввода логина и пароля"""
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X)
        
        # Поле логина
        ttk.Label(input_frame, text="Логин:").pack(anchor=tk.W)
        self.username_entry = ttk.Entry(input_frame, width=14)
        self.username_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Поле пароля
        ttk.Label(input_frame, text="Пароль:").pack(anchor=tk.W)
        self.password_entry = ttk.Entry(input_frame, show='•', width=14)
        self.password_entry.pack(fill=tk.X)
        self.password_entry.bind('<Return>', lambda e: self.authenticate())

    def _create_auth_switcher(self, parent):
        """Создание переключателей типа авторизации"""
        self.auth_frame = ttk.LabelFrame(parent, 
                                       text="Тип авторизации", 
                                       padding=(10, 5, 10, 10))
        
        ttk.Radiobutton(
            self.auth_frame,
            text="Локальная учетная запись",
            variable=self.auth_type,
            value="local"
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Radiobutton(
            self.auth_frame,
            text="Доменная учетная запись",
            variable=self.auth_type,
            value="domain"
        ).pack(anchor=tk.W, pady=2)
        
        self.auth_frame.pack(fill=tk.X, pady=(10, 0))

    def _create_action_buttons(self, parent):
        """Создание кнопок действий"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        # Основная кнопка входа
        login_btn = ttk.Button(
            btn_frame, 
            text="ВОЙТИ", 
            command=self.authenticate,
            style='Primary.TButton',
            width=15
        )
        login_btn.pack(side=tk.LEFT, expand=True)
        
        # Кнопка свертывания
        ttk.Button(
            btn_frame,
            text="Свернуть",
            command=self.minimize_to_tray,
            width=10
        ).pack(side=tk.RIGHT)

    def _handle_auth_switcher(self):
        """Управление видимостью переключателей авторизации"""
        if self._check_advanced_mode():
            self.auth_frame.pack(fill=tk.X, pady=(10, 0))
            self.window.geometry("320x220")
        else:
            self.auth_frame.pack_forget()
            self.window.geometry("320x180")

    def minimize_to_tray(self):
        """Свернуть окно в трей"""
        self.window.withdraw()

    def restore_from_tray(self):
        """Восстановить окно из трея"""
        self.window.deiconify()
        self._center_window()

    def quit_application(self):
        """Завершение работы приложения"""
        if self.tray_icon:
            self.tray_icon.stop()
        self.window.destroy()
        self.master.quit()

    def _center_window(self):
        """Центрирование окна на экране"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'+{x}+{y}')

    def _check_advanced_mode(self):
        """Проверка наличия флага расширенного режима"""
        return any(arg.lower() == "--advanced-auth" for arg in sys.argv)

    def authenticate(self):
        """Аутентификация пользователя"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        is_local = self.auth_type.get() == "local"
        
        if not username or not password:
            messagebox.showwarning("Ошибка", "Введите имя пользователя и пароль")
            return
        
        try:
            if self._check_credentials(username, password, is_local):
                self._on_auth_success(is_local, username)
            else:
                messagebox.showerror("Ошибка", "Неверные учетные данные")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка подключения: {str(e)}")

    def _check_credentials(self, username, password, is_local):
        """Проверка учетных данных"""
        if is_local:
            LOCAL_USERS = {"admin": "root", "user": "usertest"}
            return LOCAL_USERS.get(username) == password
        else:
            try:
                server = Server('ldap://kifr-ru.local', get_info=ALL)
                conn = Connection(server, user=f"KIFR-RU\\{username}", 
                               password=password)
                
                if not conn.bind():
                    return False
                
                return self._check_group_membership(conn, username)
                
            except Exception as e:
                raise Exception(f"LDAP ошибка: {str(e)}")
            finally:
                if 'conn' in locals() and conn.bound:
                    conn.unbind()

    def _check_group_membership(self, conn, username):
        """Проверка принадлежности к группе AD"""
        search_base = 'dc=kifr-ru,dc=local'
        search_filter = f'(sAMAccountName={username})'
        attributes = ['distinguishedName']
        
        conn.search(search_base, search_filter, 
                  search_scope=SUBTREE, 
                  attributes=attributes)
        
        if not conn.entries:
            return False
            
        user_dn = conn.entries[0].distinguishedName.value
        group_name = "LSG-GS-KEYCLOAK-OMNI-ALL_GROUPS-ANALYTICS"
        group_filter = f'(&(objectClass=group)(cn={group_name}))'
        
        conn.search(search_base, group_filter, 
                  search_scope=SUBTREE, 
                  attributes=['distinguishedName'])
        
        if not conn.entries:
            return False
            
        group_dn = conn.entries[0].distinguishedName.value
        return self._is_user_in_group(conn, user_dn, group_dn)
    
    def _is_user_in_group(self, conn, user_dn, group_dn, visited=None):
        """Рекурсивная проверка принадлежности пользователя к группе"""
        if visited is None:
            visited = set()
        
        group_dn_lower = group_dn.lower()
        if group_dn_lower in visited:
            return False
        visited.add(group_dn_lower)
        
        conn.search(group_dn, '(objectClass=group)', 
                  search_scope=SUBTREE,
                  attributes=['member'])
        
        if not conn.entries:
            return False
        
        for member_dn in conn.entries[0].member.values:
            member_dn_lower = member_dn.lower()
            
            if member_dn_lower == user_dn.lower():
                return True
                
            if 'CN=FS_710_IT-support_omni_l2' in member_dn:
                if self._is_user_in_group(conn, user_dn, member_dn, visited):
                    return True
                    
        return False

    def _on_auth_success(self, is_local, username):
        """Действия после успешной авторизации"""
        messagebox.showinfo("Успешно", "Авторизация прошла успешно!")
        self.on_success(is_admin=True)
        self.window.destroy()
        if self.tray_icon:
            self.tray_icon.stop()