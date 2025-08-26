import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timezone, timedelta
import jwt
import pyperclip

class JWTAnalyzerApp:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.window = ttk.Frame(parent_window)  
        self.window.pack(fill=tk.BOTH, expand=True)
        
        self.create_widgets()
        self.auto_paste_from_clipboard()
    
    def create_widgets(self):
        input_frame = ttk.LabelFrame(self.window, padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(input_frame, text="JWT Токен:").grid(row=0, column=0, sticky=tk.W)
        
        self.token_entry = ttk.Entry(input_frame, width=65)
        self.token_entry.grid(row=1, column=0, padx=5, pady=5, ipady=10, sticky=tk.W+tk.E)
        
        ttk.Label(input_frame, text="Секретный ключ (опционально):").grid(row=2, column=0, sticky=tk.W)
        self.key_entry = ttk.Entry(input_frame, width=65)
        self.key_entry.grid(row=3, column=0, padx=5, pady=5, ipady=10, sticky=tk.W+tk.E)

        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=4, column=0, columnspan=1, pady=10)
        
        self.analyze_btn = ttk.Button(button_frame, text="Декод токена", command=self.analyze_token)
        self.analyze_btn.pack(side=tk.LEFT, padx=3)
        
        self.clear_btn = ttk.Button(button_frame, text="Очистить", command=self.clear_fields)
        self.clear_btn.pack(side=tk.LEFT, padx=3)
        
        results_frame = ttk.LabelFrame(self.window, text="Результат:", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD)
        self.results_text.pack(fill=tk.BOTH, expand=True)


    def auto_paste_from_clipboard(self):
        """Автоматическая вставка из буфера обмена при инициализации"""
        try:
            clipboard_text = pyperclip.paste().strip()
            if self.is_valid_jwt(clipboard_text):
                self.token_entry.delete(0, tk.END)
                self.token_entry.insert(0, clipboard_text)
        except Exception as e:
            messagebox.showerror("Error", f"Ошибка чтения буфера: {str(e)}")

    def is_valid_jwt(self, token):
        """Проверка формата JWT"""
        return token.count(".") == 2 and len(token) > 30
    
    def paste_from_clipboard(self):
        try:
            clipboard_text = pyperclip.paste()
            if clipboard_text:
                self.token_entry.delete(0, tk.END)
                self.token_entry.insert(0, clipboard_text)
        except Exception as e:
            messagebox.showerror("Error", f"Не удалось вставить из буфера обмена: {str(e)}")
    
    def clear_fields(self):
        """Очищает все поля"""
        self.token_entry.delete(0, tk.END)
        self.key_entry.delete(0, tk.END)
        self.results_text.delete(1.0, tk.END)
    
    def analyze_token(self):
        token = self.token_entry.get()
        secret_key = self.key_entry.get() or None
        
        if not token:
            messagebox.showerror("Error", "Введите токен")
            return
        
        self.results_text.delete(1.0, tk.END)
        
        try:
            if token.count(".") != 2:
                raise ValueError("Неверный формат токена JWT: ожидается 3 части, разделенные точками")

            decoded_token = jwt.decode(token, options={'verify_signature': False}, algorithms=["HS256"])
            
            self.results_text.insert(tk.END, "="*70 + "\n")
            self.results_text.insert(tk.END, "TОсновная информация о токене:\n")
            self.results_text.insert(tk.END, "="*70 + "\n\n")
            
            for key, value in decoded_token.items():
                self.results_text.insert(tk.END, f"{key}: {value}\n\n")

            if secret_key:
                try:
                    jwt.decode(token, key=secret_key, algorithms=['HS256'], options={'verify_signature': True})
                    self.results_text.insert(tk.END, "\n" + "="*70 + "\n")
                    self.results_text.insert(tk.END, "\nПодпись токена успешно проверена")
                except jwt.InvalidSignatureError:
                    self.results_text.insert(tk.END, "\n" + "="*70 + "\n")
                    self.results_text.insert(tk.END, "Warning: \nНеверная подпись токена!")

            if "exp" in decoded_token:
                expiration_time = datetime.fromtimestamp(decoded_token["exp"])
                current_time = datetime.now()
                
                self.results_text.insert(tk.END, "\n" + "="*70 + "\n")
                self.results_text.insert(tk.END, "Анализ действительности токена:\n")
                self.results_text.insert(tk.END, "="*70 + "\n\n")
                
                if current_time > expiration_time:
                    self.results_text.insert(tk.END, "Warning: Токен не действителен!\n")
                else:
                    time_remaining = expiration_time - current_time
                    seconds_remaining = time_remaining.total_seconds()
                    
                    hours = int(seconds_remaining // 3600)
                    minutes = int((seconds_remaining % 3600) // 60)
                    seconds = int(seconds_remaining % 60)
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
                    self.results_text.insert(tk.END, f"Токен действует: {time_str}\n")

            if "iat" in decoded_token:
                issued_at_time = datetime.fromtimestamp(decoded_token["iat"], timezone.utc)
                self.results_text.insert(tk.END, "\n" + "="*70 + "\n")
                self.results_text.insert(tk.END, f"Токен выпущен : {issued_at_time}\n")

        except jwt.exceptions.DecodeError:
            messagebox.showerror("Error", "Неверный формат токена или подписи")
        except jwt.ExpiredSignatureError:
            messagebox.showwarning("Warning", "Токен не действителен")
        except jwt.InvalidTokenError:
            messagebox.showerror("Error", "Недействительный токен JWT или подпись")
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", f"Произошла непредвиденная ошибка: {str(e)}")