import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json

class BalanceChecker:
    def __init__(self, parent):
        self.window = ttk.Frame(parent, padding=10)
        
        # Заголовок
        ttk.Label(self.window, text="Проверка баланса карты", font=("Arial", 11)).pack(pady=(0, 7))
        
        # Поле ввода номера карты
        input_frame = ttk.Frame(self.window)
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="Номер карты:").pack(side=tk.LEFT, padx=(0, 5))
        self.card_entry = ttk.Entry(input_frame, width=20)
        self.card_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Кнопка запроса
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.check_btn = ttk.Button(btn_frame, text="Проверить баланс", command=self.check_balance)
        self.check_btn.pack()
        self.clear_btn = ttk.Button(btn_frame, text="Очистить", command=self.clear_output)
        self.clear_btn.pack()
        
        # Поле вывода результата
        result_frame = ttk.Frame(self.window)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        ttk.Label(result_frame, text="Результат запроса:").pack(anchor=tk.W)
        self.result_text = scrolledtext.ScrolledText(result_frame, height=10, state='normal')
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Добавляем обработчик очистки при фокусе
        self.card_entry.bind("<FocusIn>", self.clear_default_text)
        
        # Устанавливаем текст по умолчанию
        self.card_entry.insert(0, "Введите номер карты")
        self.card_entry.config(foreground='grey')
    
    def clear_default_text(self, event):
        if self.card_entry.get() == "Введите номер карты":
            self.card_entry.delete(0, tk.END)
            self.card_entry.config(foreground='black')

    def clear_output(self):
        self.card_entry.delete(0, tk.END)
        self.card_entry.insert(0, "Введите номер карты")
        self.card_entry.config(foreground='grey')
        self.result_text.delete(1.0, tk.END)
    
    def check_balance(self):
        card_number = self.card_entry.get().strip()
        
        # Проверка ввода
        if not card_number or card_number == "Введите номер карты":
            messagebox.showerror("Ошибка", "Введите номер карты")
            return
            
        # Валидация номера карты (только цифры)
        if not card_number.isdigit():
            messagebox.showerror("Ошибка", "Номер карты должен содержать только цифры")
            return
            
        # Показываем статус выполнения
        self.check_btn.config(state=tk.DISABLED, text="Запрос...")
        self.window.update()
        
        try:
            # КОРРЕКТНОЕ ФОРМИРОВАНИЕ URL С КАВЫЧКАМИ %27
            session_id = "4aab0bdd-8982-4fd1-981a-2f30a3336cea"
            url = f"https://prod-officesrv.hoff.ru/CustomerOfficeService/Balance/GetAllByCardOrPhone/"
            params = {
                'sessionId': f"'{session_id}'",  # Добавляем кавычки
                'card': f"'{card_number}'"       # Добавляем кавычки
            }
            
            # Выполняем запрос с таймаутом
            response = requests.get(url, params=params, timeout=10)
            
            # Проверяем статус ответа
            if response.status_code != 200:
                error_msg = f"{response.status_code} {response.reason}:\n{response.text}"
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, error_msg)
                messagebox.showerror("Ошибка сервера", error_msg)
                return
                
            # Форматируем JSON ответ
            try:
                data = response.json()
                formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, formatted_json)
            except json.JSONDecodeError:
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, response.text)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка запроса", f"Ошибка: {str(e)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неизвестная ошибка: {str(e)}")
        finally:
            self.check_btn.config(state=tk.NORMAL, text="Проверить баланс")
